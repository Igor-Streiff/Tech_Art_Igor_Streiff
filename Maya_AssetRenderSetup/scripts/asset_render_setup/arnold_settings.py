"""Arnold render globals."""

from __future__ import annotations

import maya.cmds as cmds

from . import config


def ensure_mtoa_loaded() -> bool:
    if not cmds.pluginInfo("mtoa", query=True, loaded=True):
        try:
            cmds.loadPlugin("mtoa", quiet=True)
        except RuntimeError:
            return False
    return cmds.pluginInfo("mtoa", query=True, loaded=True)


def ensure_arnold_options() -> bool:
    """Create defaultArnold* nodes without opening Render Settings UI."""
    if cmds.objExists("defaultArnoldRenderOptions"):
        return True
    if not ensure_mtoa_loaded():
        return False
    try:
        from mtoa.core import createOptions

        createOptions()
    except ImportError:
        return False
    return cmds.objExists("defaultArnoldRenderOptions")


def _ensure_renderer_arnold(log: list[str]) -> None:
    """Switch to Arnold if needed; tolerate MtoA UI refresh when panel is closed."""
    try:
        current = str(cmds.getAttr("defaultRenderGlobals.currentRenderer") or "").lower()
    except RuntimeError:
        current = ""
    if current == "arnold":
        log.append("Renderer: Arnold")
        return
    try:
        cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
        log.append("Renderer: Arnold")
    except RuntimeError as exc:
        # MtoA 2027 may try to refresh arnoldTabLayout when Render Settings is closed.
        log.append(
            "WARNING: Could not switch renderer via script "
            f"({exc}). Set Arnold manually in Render Settings if needed."
        )


def apply_arnold_settings() -> list[str]:
    log: list[str] = []
    ensure_arnold_options()
    _ensure_renderer_arnold(log)

    cmds.setAttr("defaultResolution.width", config.RES_WIDTH)
    cmds.setAttr("defaultResolution.height", config.RES_HEIGHT)
    cmds.setAttr("defaultResolution.deviceAspectRatio", config.RES_ASPECT)
    log.append(f"Resolution: {config.RES_WIDTH}x{config.RES_HEIGHT}")

    opts = "defaultArnoldRenderOptions"
    if not cmds.objExists(opts):
        log.append("WARNING: defaultArnoldRenderOptions not found.")
        return log

    _set_int(opts, ["AASamples", "cameraAA", "aaSamples"], config.AA_SAMPLES, log, "AA")
    _set_int(
        opts,
        ["GIDiffuseSamples", "GI_diffuse_samples", "diffuseSamples"],
        config.DIFFUSE_SAMPLES,
        log,
        "Diffuse",
    )
    _set_int(
        opts,
        ["GISpecularSamples", "GI_specular_samples", "specularSamples"],
        config.SPECULAR_SAMPLES,
        log,
        "Specular",
    )
    _set_int(
        opts,
        ["GITransmissionSamples", "GI_transmission_samples", "transmissionSamples"],
        config.TRANSMISSION_SAMPLES,
        log,
        "Transmission",
    )
    _set_int(
        opts,
        ["GISssSamples", "GI_sss_samples", "sssSamples"],
        config.SSS_SAMPLES,
        log,
        "SSS",
    )
    return log


def _set_int(node: str, attrs: list[str], value: int, log: list[str], label: str) -> None:
    for attr in attrs:
        plug = f"{node}.{attr}"
        if cmds.objExists(plug):
            cmds.setAttr(plug, value)
            log.append(f"  {label} samples: {value}")
            return
    log.append(f"  {label} samples: not set (attr not found)")
