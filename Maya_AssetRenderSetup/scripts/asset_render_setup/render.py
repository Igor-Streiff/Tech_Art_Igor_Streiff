"""Fast Arnold render to PNG (single camera or contact sheet)."""

from __future__ import annotations

import glob
import os
import re
import time
from dataclasses import replace
from datetime import datetime

import maya.cmds as cmds

from . import arnold_settings, bbox, config, core
from .config import RigOptions


def _scene_base_name() -> str:
    scene = cmds.file(query=True, sceneName=True, shortName=True)
    if scene:
        return os.path.splitext(scene)[0]
    return "untitled"


def _find_camera_by_name(target: str) -> str | None:
    """Locate a camera by its desired short name, tolerating numeric suffixes."""
    if cmds.objExists(target):
        return target

    if cmds.objExists(config.RIG_GRP):
        for node in cmds.listRelatives(
            config.RIG_GRP, allDescendents=True, type="transform", fullPath=True,
        ) or []:
            if bbox.short_name(node) == target:
                return node

    for cam_shape in cmds.ls(type="camera", long=True) or []:
        if bbox.short_name(cam_shape).startswith("front") or \
                bbox.short_name(cam_shape).startswith("persp") or \
                bbox.short_name(cam_shape).startswith("side") or \
                bbox.short_name(cam_shape).startswith("top"):
            continue
        parents = cmds.listRelatives(cam_shape, parent=True, fullPath=True) or []
        if not parents:
            continue
        parent = parents[0]
        short = bbox.short_name(parent)
        if short == target:
            return parent
        if short.startswith(target) and short[len(target):].isdigit():
            return parent
    return None


def _find_render_camera() -> str | None:
    return _find_camera_by_name(config.CAM_NAME)


def _find_all_render_cameras() -> list[tuple[str, str]]:
    cam_specs = [
        (config.CAM_NAME, "main"),
        (config.CAM_SIDE_NAME, "side"),
        (config.CAM_HIGH_NAME, "high"),
    ]
    found: list[tuple[str, str]] = []
    for cam_name, suffix in cam_specs:
        node = _find_camera_by_name(cam_name)
        if node:
            found.append((node, suffix))
    return found


def _ensure_render_camera() -> str:
    cam = _find_render_camera()
    if not cam:
        existing = cmds.ls(f"{config.RIG_PREFIX}*", type="transform") or []
        hint = f" Found rig nodes: {existing}" if existing else " No rig nodes found."
        raise RuntimeError(
            f"Camera '{config.CAM_NAME}' not found.{hint} "
            "Re-run Create Setup with the Camera checkbox enabled."
        )
    cmds.setAttr(f"{cam}.renderable", 1)
    if cmds.objExists("persp.renderable"):
        cmds.setAttr("persp.renderable", 0)
    return cam


def _notify_missing_setup() -> None:
    cmds.confirmDialog(
        title="Asset Render Setup — Fast Render",
        message=(
            f"Fast Render needs an existing setup with camera:\n"
            f"  {config.CAM_NAME}\n\n"
            "Run Create Setup first (Camera checkbox enabled),\n"
            "then try Fast Render again."
        ),
        button=["OK"],
        defaultButton="OK",
    )


def _active_aov_labels() -> list[str]:
    """Names of Arnold AOV nodes currently enabled for disk output."""
    labels: list[str] = []
    for node in cmds.ls(type="aiAOV") or []:
        plug = f"{node}.enabled"
        if cmds.objExists(plug) and cmds.getAttr(plug):
            name_plug = f"{node}.name"
            if cmds.objExists(name_plug):
                labels.append(str(cmds.getAttr(name_plug)))
            else:
                labels.append(bbox.short_name(node))
    return labels


def _project_images_dir() -> str:
    project = cmds.workspace(query=True, rootDirectory=True) or ""
    try:
        images_rel = cmds.workspace(fileRuleEntry="images") or "images"
    except RuntimeError:
        images_rel = "images"
    return os.path.normpath(os.path.join(project, images_rel))


def _configure_render_globals(prefix_no_ext: str) -> None:
    """Point Arnold at an absolute PNG prefix (does not change AOVs)."""
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    cmds.setAttr("defaultRenderGlobals.imageFormat", 32)  # PNG
    cmds.setAttr(
        "defaultRenderGlobals.imageFilePrefix",
        prefix_no_ext.replace("\\", "/"),
        type="string",
    )
    cmds.setAttr("defaultRenderGlobals.animation", 0)
    cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", 0)
    cmds.setAttr("defaultRenderGlobals.periodInExt", 1)
    cmds.setAttr("defaultRenderGlobals.extensionPadding", 1)
    cmds.setAttr("defaultRenderGlobals.useFrameExt", 0)

    if cmds.objExists("defaultArnoldDriver.aiTranslator"):
        try:
            cmds.setAttr("defaultArnoldDriver.aiTranslator", "png", type="string")
        except RuntimeError:
            pass


def _collect_png_outputs(prefix_no_ext: str, since_epoch: float | None = None) -> list[str]:
    """All PNG files written for this render prefix."""
    directory = os.path.dirname(prefix_no_ext) or "."
    base = os.path.basename(prefix_no_ext)
    images_dir = _project_images_dir()

    patterns = [
        os.path.join(directory, f"{base}*.png"),
        os.path.join(images_dir, f"{base}*.png"),
    ]

    found: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for path in glob.glob(pattern):
            norm = os.path.normpath(path)
            if norm in seen or not norm.lower().endswith(".png"):
                continue
            if since_epoch is not None:
                try:
                    if os.path.getmtime(norm) < since_epoch - 1.0:
                        continue
                except OSError:
                    continue
            seen.add(norm)
            found.append(norm)
    return sorted(found)


def _wait_for_png_outputs(prefix_no_ext: str, since_epoch: float) -> list[str]:
    """Poll until Arnold flushes PNGs or timeout."""
    directory = os.path.dirname(prefix_no_ext) or "."
    deadline = time.time() + 3.0
    while time.time() < deadline:
        outputs = _collect_png_outputs(prefix_no_ext, since_epoch=since_epoch)
        if outputs:
            return outputs
        time.sleep(0.25)

    outputs = _collect_png_outputs(prefix_no_ext, since_epoch=since_epoch)
    if outputs:
        return outputs

    # Last resort: fresh PNGs in the output folder matching this prefix basename.
    base = os.path.basename(prefix_no_ext)
    recent: list[str] = []
    if os.path.isdir(directory):
        for name in os.listdir(directory):
            if not name.lower().endswith(".png") or not name.startswith(base):
                continue
            path = os.path.normpath(os.path.join(directory, name))
            try:
                if os.path.getmtime(path) >= since_epoch - 1.0:
                    recent.append(path)
            except OSError:
                continue
    return sorted(recent)


def _sort_stem_outputs(outputs: list[str], stem: str) -> list[str]:
    """Sort render outputs: ``stem.png``, then ``stem_1.png``, ``stem_2.png``, …"""

    def _key(path: str) -> tuple[int, int, str]:
        name = os.path.splitext(os.path.basename(path))[0]
        if name == stem:
            return (0, 0, name)
        if name.startswith(f"{stem}_"):
            suffix = name[len(stem) + 1:]
            if suffix.isdigit():
                return (1, int(suffix), name)
            return (2, 0, name)
        return (3, 0, name)

    return sorted({os.path.normpath(p) for p in outputs}, key=_key)


def _identify_beauty_source(
    outputs: list[str],
    stem: str,
    aov_labels: list[str],
) -> str | None:
    """
    Pick which PNG is the beauty pass.

    With AOVs active, MtoA often writes the first AOV (e.g. albedo) to ``stem.png``
    and the beauty to ``stem_1.png`` — not the other way around.
    """
    if not outputs:
        return None
    if len(outputs) == 1:
        return outputs[0]

    directory = os.path.dirname(outputs[0]) or "."
    stem_path = os.path.normpath(os.path.join(directory, f"{stem}.png"))
    numbered = [
        p for p in outputs
        if re.match(rf"^{re.escape(stem)}_\d+$", os.path.splitext(os.path.basename(p))[0])
    ]

    sidecar_labels = _sidecar_label_candidates(aov_labels)
    if stem_path in outputs and numbered and sidecar_labels:
        first = sidecar_labels[0]
        # When albedo (or mask) occupies the bare prefix, beauty is usually the last numbered file.
        if first in ("albedo", "mask"):
            return sorted(
                numbered,
                key=lambda p: int(os.path.splitext(os.path.basename(p))[0].rsplit("_", 1)[-1]),
            )[-1]

    if stem_path in outputs:
        return stem_path

    try:
        return max(outputs, key=lambda p: os.path.getsize(p))
    except (OSError, ValueError):
        return outputs[0]


def _finalize_render_outputs(
    prefix: str,
    *,
    beauty_only: bool,
    aov_labels: list[str],
    render_started: float,
) -> tuple[str, list[str]]:
    """
    Move/rename Arnold outputs to explicit filenames: ``{stem}_beauty.png``, ``{stem}_albedo.png``, …
    """
    directory = os.path.dirname(prefix) or "."
    stem = os.path.basename(prefix)
    beauty_dest = os.path.normpath(os.path.join(directory, f"{stem}_beauty.png"))

    outputs = _wait_for_png_outputs(prefix, render_started)
    if not outputs:
        raise RuntimeError(
            f"Render completed but no PNG was written for prefix '{stem}'.\n"
            f"  Also searched: {_project_images_dir()}"
        )

    if beauty_only:
        src = _identify_beauty_source(outputs, stem, [])
        if os.path.isfile(beauty_dest):
            os.remove(beauty_dest)
        if src != beauty_dest:
            os.replace(src, beauty_dest)
        _cleanup_extra_pngs(prefix, beauty_dest)
        return beauty_dest, [beauty_dest]

    beauty_src = _identify_beauty_source(outputs, stem, aov_labels)
    if not beauty_src:
        raise RuntimeError(f"Could not identify beauty PNG among: {outputs}")

    if os.path.isfile(beauty_dest):
        os.remove(beauty_dest)
    if os.path.normpath(beauty_src) != beauty_dest:
        os.replace(beauty_src, beauty_dest)

    # Remaining files → named AOV sidecars (in Arnold write order).
    time.sleep(0.1)
    remaining = [
        p for p in _collect_png_outputs(prefix, since_epoch=render_started - 1.0)
        if os.path.normpath(p) != beauty_dest and os.path.isfile(p)
    ]
    remaining = _sort_stem_outputs(remaining, stem)

    labels = _sidecar_label_candidates(aov_labels)
    final_paths = [beauty_dest]
    for idx, path in enumerate(remaining):
        label = labels[idx] if idx < len(labels) else f"pass{idx + 1}"
        new_path = os.path.normpath(os.path.join(directory, f"{stem}_{label}.png"))
        if os.path.normpath(path) != new_path:
            if os.path.isfile(new_path):
                os.remove(new_path)
            os.replace(path, new_path)
        final_paths.append(new_path)

    return beauty_dest, final_paths


def _sanitize_label(name: str) -> str:
    return re.sub(r"[^\w\-]+", "_", name.strip()).strip("_").lower() or "pass"


def _render_stem(base: str, stamp: str, view: str | None = None) -> str:
    """Build output filename stem (no extension, no path)."""
    if config.RENDER_USE_TIMESTAMP and stamp:
        if view:
            return f"{base}_{stamp}_{view}"
        return f"{base}_{stamp}"
    if view:
        return f"{base}_{view}"
    return base


def _sidecar_label_candidates(aov_labels: list[str]) -> list[str]:
    """Human-readable suffixes for Arnold numbered sidecars (_1, _2, …)."""
    labels: list[str] = []
    if cmds.objExists("defaultRenderGlobals.alphaChannel"):
        try:
            if cmds.getAttr("defaultRenderGlobals.alphaChannel"):
                labels.append("mask")
        except RuntimeError:
            pass
    for label in aov_labels:
        if label in config.PNG_INCOMPATIBLE_AOVS:
            continue
        clean = _sanitize_label(label)
        if clean not in labels:
            labels.append(clean)
    return labels


def _snapshot_aov_enabled() -> dict[str, bool]:
    state: dict[str, bool] = {}
    for node in cmds.ls(type="aiAOV") or []:
        plug = f"{node}.enabled"
        if cmds.objExists(plug):
            state[node] = bool(cmds.getAttr(plug))
    return state


def _set_aov_enabled(state: dict[str, bool], value: bool) -> None:
    for node in state:
        plug = f"{node}.enabled"
        if cmds.objExists(plug):
            try:
                cmds.setAttr(plug, int(value))
            except RuntimeError:
                pass


def _restore_aov_enabled(state: dict[str, bool]) -> None:
    for node, enabled in state.items():
        plug = f"{node}.enabled"
        if cmds.objExists(plug):
            try:
                cmds.setAttr(plug, int(enabled))
            except RuntimeError:
                pass


def _cleanup_extra_pngs(prefix_no_ext: str, keep_path: str) -> int:
    keep_norm = os.path.normpath(keep_path)
    removed = 0
    for path in _collect_png_outputs(prefix_no_ext):
        if path == keep_norm:
            continue
        try:
            os.remove(path)
            removed += 1
        except OSError:
            pass
    return removed


def _render_one_camera(
    cam: str,
    prefix: str,
    *,
    beauty_only: bool,
) -> tuple[str, list[str]]:
    """
    Render one camera pass.

    Returns (beauty_path, all_output_paths).
    When *beauty_only* is False, scene AOVs / alpha settings are left untouched.
    """
    aov_state = _snapshot_aov_enabled() if beauty_only else {}
    aov_labels = _active_aov_labels() if not beauty_only else []
    render_started = time.time()

    try:
        if beauty_only:
            _set_aov_enabled(aov_state, False)

        cmds.setAttr(f"{cam}.renderable", 1)
        cmds.lookThru(cam)
        _configure_render_globals(prefix)

        try:
            cmds.arnoldRender(
                cam=cam,
                width=config.RES_WIDTH,
                height=config.RES_HEIGHT,
            )
        except (RuntimeError, TypeError):
            cmds.render(cam)

        return _finalize_render_outputs(
            prefix,
            beauty_only=beauty_only,
            aov_labels=aov_labels,
            render_started=render_started,
        )
    finally:
        if beauty_only:
            _restore_aov_enabled(aov_state)


def fast_render(
    output_dir: str,
    options: RigOptions | None = None,
    auto_setup_if_missing: bool = False,
) -> list[str]:
    """
    Render PNG(s) to *output_dir* using the scene's Arnold settings.

    By default respects active AOVs and Render Settings (Common → alpha mask, etc.).
    Set ``options.beauty_only=True`` to temporarily disable AOV disk output and
    keep only the beauty PNG per camera.

    Requires an existing setup with ``config.CAM_NAME`` unless
    *auto_setup_if_missing* is True.
    """
    log: list[str] = []
    t0 = time.time()
    opts = options if options is not None else RigOptions.all_enabled()
    beauty_only = opts.beauty_only

    if not output_dir or not output_dir.strip():
        raise ValueError("Output folder is required.")

    output_dir = os.path.normpath(output_dir.strip())
    os.makedirs(output_dir, exist_ok=True)

    if not arnold_settings.ensure_mtoa_loaded():
        raise RuntimeError("Arnold (mtoa) is not available.")

    cam = _find_render_camera()
    if not cam:
        if auto_setup_if_missing:
            setup_opts = replace(opts, camera=True)
            if cmds.objExists(config.RIG_GRP):
                log.append(
                    f"Camera '{config.CAM_NAME}' missing — re-running Create Setup (Camera ON)..."
                )
            else:
                log.append("No rig found — running Create Setup (Camera ON)...")
            log.extend(core.create_setup(setup_opts))
        else:
            _notify_missing_setup()
            raise RuntimeError(
                f"Camera '{config.CAM_NAME}' not found. Run Create Setup first."
            )

    cam = _ensure_render_camera()
    arnold_settings.apply_arnold_settings()

    active_aovs = _active_aov_labels()
    if beauty_only:
        log.append("Fast Render mode: beauty only (scene AOVs temporarily disabled).")
    elif active_aovs:
        log.append(
            f"Scene AOVs enabled ({len(active_aovs)}): {', '.join(active_aovs)}"
        )
        log.append(
            "  Extra PNGs per camera are expected (from Render Settings, not a 2nd tool render)."
        )
        log.append(
            "  For beauty only: enable 'Beauty only' in the UI, or disable AOVs in Arnold → AOVs."
        )
    else:
        log.append(
            "No Arnold AOVs enabled. If you still get a 2nd PNG, check "
            "Render Settings → Common → Alpha channel (Mask) on renderable cameras."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S") if config.RENDER_USE_TIMESTAMP else ""
    base = _scene_base_name()
    use_tri = opts.tri_cam
    cameras = _find_all_render_cameras() if use_tri else []

    if not config.RENDER_USE_TIMESTAMP:
        log.append(
            f"Output naming: {base}_beauty.png (+ {{aov}}.png when AOVs are on; see config.py for timestamp)"
        )

    beauty_count = 0
    if len(cameras) > 1:
        for cam_node, suffix in cameras:
            stem = _render_stem(base, stamp, view=suffix)
            prefix = os.path.join(output_dir, stem)
            beauty_path, all_paths = _render_one_camera(
                cam_node, prefix, beauty_only=beauty_only,
            )
            log.append(f"Saved beauty: {beauty_path}")
            extras = [p for p in all_paths if os.path.normpath(p) != os.path.normpath(beauty_path)]
            for extra in extras:
                log.append(f"  + AOV: {os.path.basename(extra)}")
            beauty_count += 1
    else:
        stem = _render_stem(base, stamp)
        prefix = os.path.join(output_dir, stem)
        beauty_path, all_paths = _render_one_camera(
            cam, prefix, beauty_only=beauty_only,
        )
        log.append(f"Saved beauty: {beauty_path}")
        extras = [p for p in all_paths if os.path.normpath(p) != os.path.normpath(beauty_path)]
        for extra in extras:
            log.append(f"  + AOV: {os.path.basename(extra)}")
        beauty_count = 1

    elapsed = time.time() - t0
    log.append(f"{beauty_count} beauty PNG(s) | {config.RES_WIDTH}x{config.RES_HEIGHT} | {elapsed:.1f}s")
    return log
