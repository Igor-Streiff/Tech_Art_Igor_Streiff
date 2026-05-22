"""Asset Render Setup — Maya UI."""

from __future__ import annotations

import os
import traceback

import maya.cmds as cmds

from . import bootstrap, config, core, render

WINDOW_NAME = "TA_AssetRenderSetupWindow"
LOG_FIELD = "TA_AssetRenderSetup_log"

_CHECKBOXES: dict[str, str] = {}
_PRESET_MENU: str = ""


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


def _read_options() -> config.RigOptions:
    preset_key = "default"
    if _PRESET_MENU:
        try:
            preset_key = cmds.optionMenu(_PRESET_MENU, query=True, value=True)
        except Exception:
            pass
    return config.RigOptions(
        camera=cmds.checkBox(_CHECKBOXES["camera"], query=True, value=True),
        cyclorama=cmds.checkBox(_CHECKBOXES["cyclorama"], query=True, value=True),
        key_light=cmds.checkBox(_CHECKBOXES["key_light"], query=True, value=True),
        fill_light=cmds.checkBox(_CHECKBOXES["fill_light"], query=True, value=True),
        rim_light=cmds.checkBox(_CHECKBOXES["rim_light"], query=True, value=True),
        uplight=cmds.checkBox(_CHECKBOXES["uplight"], query=True, value=True),
        skydome=cmds.checkBox(_CHECKBOXES["skydome"], query=True, value=True),
        arnold_settings=cmds.checkBox(_CHECKBOXES["arnold_settings"], query=True, value=True),
        tri_cam=cmds.checkBox(_CHECKBOXES["tri_cam"], query=True, value=True),
        reference_kit=cmds.checkBox(_CHECKBOXES["reference_kit"], query=True, value=True),
        lighting_preset=preset_key,
        beauty_only=cmds.checkBox(_CHECKBOXES["beauty_only"], query=True, value=True),
    )


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

    cmds.window(WINDOW_NAME, title="Asset Render Setup", widthHeight=(380, 720))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnOffset=("both", 12))

    cmds.separator(height=8, style="none")
    cmds.text(label="Asset Render Setup", font="boldLabelFont", align="center")
    cmds.text(label=f"v{config.__version__}", align="center")
    cmds.separator(height=8, style="in")

    cmds.text(label="Include in setup:", align="left", font="smallBoldLabelFont")

    def _cb(label: str, key: str, default: bool = True) -> None:
        _CHECKBOXES[key] = cmds.checkBox(label=label, value=default, align="left")

    _cb("Camera", "camera")
    _cb("Cyclorama (floor + curved backdrop)", "cyclorama")
    _cb("Key light", "key_light")
    _cb("Fill light", "fill_light")
    _cb("Rim light", "rim_light")
    _cb("Uplight (contrapicado / hero light)", "uplight", default=False)
    _cb("Skydome (ambient fill)", "skydome")
    _cb("Arnold settings (1920x1080, samples)", "arnold_settings")

    cmds.separator(height=4, style="none")
    cmds.text(label="Extras:", align="left", font="smallBoldLabelFont")
    _cb("Tri-Cam (main + side + high)", "tri_cam", default=False)
    _cb("Reference kit (chrome + gray spheres)", "reference_kit", default=False)

    cmds.separator(height=4, style="none")
    cmds.text(label="Lighting preset:", align="left", font="smallBoldLabelFont")
    global _PRESET_MENU
    _PRESET_MENU = cmds.optionMenu()
    for key in config.LIGHTING_PRESETS:
        cmds.menuItem(label=key)

    cmds.separator(height=8, style="in")
    cmds.text(label="Fast Render:", align="left", font="smallBoldLabelFont")
    _cb(
        "Beauty only (ignore scene AOVs / extra passes)",
        "beauty_only",
        default=False,
    )
    cmds.text(
        label="Off = respect Arnold Render Settings (AOVs, alpha mask, etc.)",
        align="left",
        font="smallObliqueLabelFont",
    )

    cmds.separator(height=4, style="none")
    cmds.text(label="Output folder:", align="left", font="smallBoldLabelFont")

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAlign=(1, "left"))
    cmds.textField("TA_AssetRenderSetup_outputField", text=saved_out)
    cmds.button(label="Browse", command=_on_browse, width=70)
    cmds.setParent("..")

    cmds.separator(height=8, style="none")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(180, 180), columnAlign2=("center", "center"))
    cmds.button(
        label="Create Setup",
        height=40,
        backgroundColor=(0.25, 0.45, 0.65),
        command=_on_create_setup,
    )
    cmds.button(
        label="Fast Render",
        height=40,
        backgroundColor=(0.35, 0.55, 0.4),
        command=_on_fast_render,
    )
    cmds.setParent("..")

    cmds.text(label="Log:", align="left", font="smallBoldLabelFont")
    cmds.scrollField(LOG_FIELD, height=160, editable=False, wordWrap=True, text="Ready.")

    cmds.separator(height=8, style="none")
    cmds.showWindow(WINDOW_NAME)
