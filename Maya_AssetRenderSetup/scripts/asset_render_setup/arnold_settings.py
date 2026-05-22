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


def apply_arnold_settings() -> list[str]:
    log: list[str] = []
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    log.append("Renderer: Arnold")

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
