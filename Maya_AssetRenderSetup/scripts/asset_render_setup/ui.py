"""Asset Render Setup — Maya UI."""

from __future__ import annotations

import os
import traceback

import maya.cmds as cmds

from . import bootstrap, config, core, render

WINDOW_NAME = "TA_AssetRenderSetupWindow"
LOG_FIELD = "TA_AssetRenderSetup_log"

_CHECKBOXES: dict[str, str] = {}
_EXPOSURE_SLIDERS: dict[str, str] = {}
# Clay state persisted between Apply / Restore clicks
_clay_saved_assignments: dict[str, str] = {}
_clay_nodes: list[str] = []   # [sg, mtl]


def _reload_modules() -> None:
    """Reload package modules so Script Editor / UI picks up file changes."""
    import importlib

    global config, core, render
    from . import (
        arnold_settings,
        bbox,
        cleanup,
        config as cfg,
        core as cr,
        render as rn,
        rig,
    )

    importlib.reload(cfg)
    importlib.reload(arnold_settings)
    importlib.reload(bbox)
    importlib.reload(cleanup)
    importlib.reload(rig)
    importlib.reload(cr)
    importlib.reload(rn)
    config = cfg
    core = cr
    render = rn


def _log(text: str) -> None:
    if not cmds.control(LOG_FIELD, exists=True):
        return
    prev = cmds.scrollField(LOG_FIELD, query=True, text=True) or ""
    cmds.scrollField(LOG_FIELD, edit=True, text=prev + text + "\n")


def _clear_log() -> None:
    if cmds.control(LOG_FIELD, exists=True):
        cmds.scrollField(LOG_FIELD, edit=True, text="")


def _get_output_dir() -> str:
    field = "TA_AssetRenderSetup_outputField"
    if cmds.control(field, exists=True):
        return cmds.textField(field, query=True, text=True) or ""
    if cmds.optionVar(exists=config.OPTIONVAR_OUTPUT_DIR):
        return cmds.optionVar(query=config.OPTIONVAR_OUTPUT_DIR) or ""
    return ""


def _save_output_dir(path: str) -> None:
    cmds.optionVar(stringValue=(config.OPTIONVAR_OUTPUT_DIR, path))


def _saved_exposure(key: str) -> float:
    optionvar = config.EXPOSURE_OPTIONVARS[key]
    default = config.EXPOSURE_DEFAULTS[key]
    if cmds.optionVar(exists=optionvar):
        value = float(cmds.optionVar(query=optionvar))
        return max(config.LIGHT_EXPOSURE_MIN, min(config.LIGHT_EXPOSURE_MAX, value))
    return default


def _persist_exposure(key: str, *_args) -> None:
    ctrl = _EXPOSURE_SLIDERS.get(key)
    if not ctrl or not cmds.control(ctrl, exists=True):
        return
    value = cmds.floatSliderGrp(ctrl, query=True, value=True)
    cmds.optionVar(floatValue=(config.EXPOSURE_OPTIONVARS[key], value))


def _read_exposure(key: str) -> float:
    ctrl = _EXPOSURE_SLIDERS.get(key)
    if ctrl and cmds.control(ctrl, exists=True):
        return float(cmds.floatSliderGrp(ctrl, query=True, value=True))
    return _saved_exposure(key)


def _exposure_slider(key: str, label: str) -> None:
    _EXPOSURE_SLIDERS[key] = cmds.floatSliderGrp(
        label=label,
        field=True,
        minValue=config.LIGHT_EXPOSURE_MIN,
        maxValue=config.LIGHT_EXPOSURE_MAX,
        value=_saved_exposure(key),
        step=config.LIGHT_EXPOSURE_STEP,
        precision=1,
        columnWidth3=(88, 44, 168),
        changeCommand=lambda *_a, k=key: _persist_exposure(k),
    )


def _read_options() -> config.RigOptions:
    def _val(key: str) -> bool:
        return cmds.checkBox(_CHECKBOXES[key], query=True, value=True)

    return config.RigOptions(
        camera=_val("camera"),
        cyclorama=_val("cyclorama"),
        key_light=_val("key_light"),
        fill_light=_val("fill_light"),
        rim_light=_val("rim_light"),
        uplight=_val("uplight"),
        skydome=_val("skydome"),
        arnold_settings=_val("arnold_settings"),
        tri_cam=False,
        cam_side=_val("cam_side"),
        cam_high=_val("cam_high"),
        cam_iso_left=_val("cam_iso_left"),
        cam_iso_right=_val("cam_iso_right"),
        reference_kit=_val("reference_kit"),
        key_exposure=_read_exposure("key"),
        fill_exposure=_read_exposure("fill"),
        rim_exposure=_read_exposure("rim"),
        uplight_exposure=_read_exposure("uplight"),
        sky_exposure=_read_exposure("sky"),
        beauty_only=_val("beauty_only"),
        clay_render=_val("clay_render"),
    )


def _on_apply_clay(*_args) -> None:
    global _clay_saved_assignments, _clay_nodes
    _clear_log()
    try:
        _reload_modules()
        shapes = render._get_asset_mesh_shapes()
        if not shapes:
            _log("No asset meshes found.")
            return
        _clay_saved_assignments = render._save_shading_assignments(shapes)

        use_ai = bool(cmds.pluginInfo("mtoa", query=True, loaded=True)
                      if cmds.pluginInfo("mtoa", query=True, registered=True) else False)
        mtl_name, sg_name = "TA_tmp_clayMtl", "TA_tmp_claySG"
        for n in (sg_name, mtl_name):
            if cmds.objExists(n):
                cmds.delete(n)

        cr, cg, cb = config.CLAY_COLOR
        if use_ai:
            mtl = cmds.shadingNode("aiStandardSurface", asShader=True, name=mtl_name)
            cmds.setAttr(f"{mtl}.baseColor", cr, cg, cb, type="double3")
            cmds.setAttr(f"{mtl}.base", 1.0)
            cmds.setAttr(f"{mtl}.metalness", 0.0)
            cmds.setAttr(f"{mtl}.specular", config.CLAY_SPECULAR)
            cmds.setAttr(f"{mtl}.specularRoughness", config.CLAY_ROUGHNESS)
        else:
            mtl = cmds.shadingNode("lambert", asShader=True, name=mtl_name)
            cmds.setAttr(f"{mtl}.color", cr, cg, cb, type="double3")

        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg_name)
        cmds.connectAttr(f"{mtl}.outColor", f"{sg}.surfaceShader", force=True)
        _clay_nodes[:] = [sg, mtl]

        for shape in shapes:
            try:
                cmds.sets(shape, forceElement=sg)
            except RuntimeError:
                pass
        _log(f"Clay applied to {len(shapes)} mesh(es). Use 'Restore materials' to revert.")
    except Exception as exc:
        _log(f"ERROR: {exc}")
        _log(traceback.format_exc())


def _on_restore_clay(*_args) -> None:
    global _clay_saved_assignments, _clay_nodes
    _clear_log()
    restored = 0
    for shape, sg in _clay_saved_assignments.items():
        if cmds.objExists(shape) and cmds.objExists(sg):
            try:
                cmds.sets(shape, forceElement=sg)
                restored += 1
            except RuntimeError:
                pass
    for node in _clay_nodes:
        if cmds.objExists(node):
            try:
                cmds.delete(node)
            except RuntimeError:
                pass
    _clay_saved_assignments.clear()
    _clay_nodes.clear()
    _log(f"Materials restored ({restored} mesh(es)).")


def _on_browse(*_args) -> None:
    start = _get_output_dir() or os.path.expanduser("~")
    paths = cmds.fileDialog2(
        fileMode=3,
        caption="Select output folder",
        okCaption="Select",
        startingDirectory=start if os.path.isdir(start) else None,
    )
    if paths:
        path = paths[0]
        cmds.textField("TA_AssetRenderSetup_outputField", edit=True, text=path)
        _save_output_dir(path)


def _on_create_setup(*_args) -> None:
    _clear_log()
    try:
        _reload_modules()
        opts = _read_options()
        lines = core.create_setup(opts)
        for line in lines:
            _log(line)
    except Exception as exc:
        _log(f"ERROR: {exc}")
        _log(traceback.format_exc())
        cmds.warning(str(exc))


def _on_fast_render(*_args) -> None:
    _clear_log()
    try:
        _reload_modules()
        out_dir = _get_output_dir()
        if not out_dir:
            raise ValueError("Choose an output folder first (Browse).")
        _save_output_dir(out_dir)
        opts = _read_options()
        lines = render.fast_render(out_dir, options=opts)
        for line in lines:
            _log(line)
    except Exception as exc:
        _log(f"ERROR: {exc}")
        _log(traceback.format_exc())
        cmds.warning(str(exc))


def show() -> None:
    bootstrap.ensure_on_path()
    _reload_modules()

    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    saved_out = ""
    if cmds.optionVar(exists=config.OPTIONVAR_OUTPUT_DIR):
        saved_out = cmds.optionVar(query=config.OPTIONVAR_OUTPUT_DIR) or ""

    cmds.window(WINDOW_NAME, title="Asset Render Setup", widthHeight=(340, 780))
    cmds.scrollLayout(horizontalScrollBarThickness=0)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=0, columnOffset=("both", 10))

    # ── Header ──────────────────────────────────────────────────────────────
    cmds.separator(height=10, style="none")
    cmds.text(label="Asset Render Setup", font="boldLabelFont", align="center")
    cmds.text(label=f"v{config.__version__}", align="center")

    def _section(title: str) -> None:
        cmds.separator(height=10, style="in")
        cmds.text(label=title, align="left", font="smallBoldLabelFont")
        cmds.separator(height=4, style="none")

    def _cb(label: str, key: str, default: bool = True) -> None:
        _CHECKBOXES[key] = cmds.checkBox(label=label, value=default, align="left")

    # ── Rig ─────────────────────────────────────────────────────────────────
    _section("Rig")
    _cb("Cyclorama  (floor + curved backdrop)", "cyclorama")
    _cb("Reference kit  (chrome + 18% gray spheres)", "reference_kit", default=False)
    _cb("Apply Arnold settings  (1920×1080, AA 7)", "arnold_settings")

    cmds.separator(height=4, style="none")
    cmds.text(label="  Cameras:", align="left", font="smallBoldLabelFont")
    cmds.separator(height=2, style="none")

    cmds.rowLayout(numberOfColumns=1, adjustableColumn=1, columnOffset1=12)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=1)
    _cb("Hero  (3/4)", "camera")
    _cb("Side", "cam_side", default=False)
    _cb("High", "cam_high", default=False)
    _cb("Iso left  (orthographic ↗)", "cam_iso_left", default=False)
    _cb("Iso right  (orthographic ↗)", "cam_iso_right", default=False)
    cmds.setParent("..")
    cmds.setParent("..")

    # ── Lights ──────────────────────────────────────────────────────────────
    _section("Lights")
    cmds.text(
        label="Exposure (EV, 0 = base) — saved in this Maya profile",
        align="left",
        font="smallObliqueLabelFont",
    )
    cmds.separator(height=4, style="none")

    _cb("Key light", "key_light")
    _exposure_slider("key", "  Key")
    cmds.separator(height=2, style="none")

    _cb("Fill light", "fill_light")
    _exposure_slider("fill", "  Fill")
    cmds.separator(height=2, style="none")

    _cb("Rim light", "rim_light")
    _exposure_slider("rim", "  Rim")
    cmds.separator(height=2, style="none")

    _cb("Uplight  (from below)", "uplight", default=False)
    _exposure_slider("uplight", "  Uplight")
    cmds.separator(height=2, style="none")

    _cb("Skydome  (ambient fill)", "skydome")
    _exposure_slider("sky", "  Skydome")

    # ── Fast Render ─────────────────────────────────────────────────────────
    _section("Fast Render")
    _cb("Clay render  (override during Fast Render)", "clay_render", default=False)
    cmds.text(
        label="  Applies matte clay for the render. For RenderView preview:",
        align="left",
        font="smallObliqueLabelFont",
    )
    cmds.separator(height=3, style="none")
    cmds.rowLayout(
        numberOfColumns=2,
        columnWidth2=(152, 152),
        columnAlign2=("center", "center"),
        columnAttach2=("both", "both"),
        columnOffset2=(2, 2),
    )
    cmds.button(
        label="Apply Clay",
        height=24,
        backgroundColor=(0.38, 0.32, 0.28),
        command=_on_apply_clay,
    )
    cmds.button(
        label="Restore materials",
        height=24,
        backgroundColor=(0.30, 0.30, 0.30),
        command=_on_restore_clay,
    )
    cmds.setParent("..")
    cmds.separator(height=6, style="none")
    _cb("Beauty only  (skip extra AOVs / passes)", "beauty_only", default=False)
    cmds.text(
        label="Off = export AOVs per Arnold Render Settings",
        align="left",
        font="smallObliqueLabelFont",
    )

    cmds.separator(height=6, style="none")
    cmds.text(label="Output folder:", align="left", font="smallBoldLabelFont")
    cmds.separator(height=2, style="none")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1)
    cmds.textField("TA_AssetRenderSetup_outputField", text=saved_out)
    cmds.button(label="Browse", command=_on_browse, width=64)
    cmds.setParent("..")

    # ── Action buttons ──────────────────────────────────────────────────────
    cmds.separator(height=10, style="none")
    cmds.rowLayout(
        numberOfColumns=2,
        columnWidth2=(155, 155),
        columnAlign2=("center", "center"),
        columnAttach2=("both", "both"),
        columnOffset2=(2, 2),
    )
    cmds.button(
        label="Create Setup",
        height=36,
        backgroundColor=(0.25, 0.45, 0.65),
        command=_on_create_setup,
    )
    cmds.button(
        label="Fast Render",
        height=36,
        backgroundColor=(0.30, 0.52, 0.38),
        command=_on_fast_render,
    )
    cmds.setParent("..")

    # ── Log ─────────────────────────────────────────────────────────────────
    cmds.separator(height=10, style="in")
    cmds.text(label="Log:", align="left", font="smallBoldLabelFont")
    cmds.scrollField(LOG_FIELD, height=120, editable=False, wordWrap=True, text="Ready.")
    cmds.separator(height=8, style="none")

    cmds.showWindow(WINDOW_NAME)
