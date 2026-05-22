"""Orchestrator: create_setup."""

from __future__ import annotations

from . import arnold_settings, bbox, cleanup, config, rig
from .config import BBox, RigOptions


def create_setup(options: RigOptions | None = None) -> list[str]:
    """
    Build render rig from current scene selection or visible meshes.
    Returns log lines for UI / Script Editor.
    """
    if options is None:
        options = RigOptions.all_enabled()

    log: list[str] = []

    if not arnold_settings.ensure_mtoa_loaded():
        raise RuntimeError("Arnold (mtoa) plugin is not available. Enable it in Plug-in Manager.")

    targets = bbox.get_targets()
    if not targets:
        raise RuntimeError("No mesh geometry found. Select your asset or add meshes to the scene.")

    bb: BBox = bbox.compute_bbox(targets)
    cx, cy, cz = bb.center
    log.append(f"BBox center=({cx:.3f}, {cy:.3f}, {cz:.3f}) size={bb.size:.3f}")
    log.append(f"Targets: {', '.join(targets[:5])}" + (" ..." if len(targets) > 5 else ""))

    cleanup.cleanup_rig()
    log.append("Cleaned previous rig.")

    log.extend(rig.build_rig(bb, options, targets=targets))

    if options.arnold_settings:
        log.append("Arnold settings:")
        log.extend(arnold_settings.apply_arnold_settings())

    log.append("=== Setup complete ===")
    if options.tri_cam and options.camera:
        log.append(f"View through any of: {', '.join(config.TRI_CAM_NAMES)}")
    else:
        log.append(f"View through {config.CAM_NAME} and run Arnold IPR.")

    return log
