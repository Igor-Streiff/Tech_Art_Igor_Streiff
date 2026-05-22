"""
Install shelf button for Asset Render Setup.

Run from Maya:
  File -> Open Script -> select this file -> Execute

That's it. Auto-runs on load. If Maya can't detect the file location,
a dialog will ask you to point to this same install.py file.

Self-contained installer (no external imports — avoids Maya module cache issues).
"""

from __future__ import annotations

import os
import sys

import maya.cmds as cmds
import maya.mel as mel


OPTIONVAR_SCRIPTS = "TA_assetRenderSetup_scriptsPath"
SHELF_LABELS = ("Asset Render", "Asset Render Setup")
SHELF_CMD_MARKERS = (
    "TA_assetRenderSetup",
    "ta_shelf_launch",
    "asset_render_setup",
    "Maya_AssetRenderSetup",
)


def _purge_stale_modules() -> None:
    """Drop cached versions so re-running the installer always loads fresh code."""
    for mod_name in list(sys.modules):
        if mod_name == "shelf_utils" or mod_name.startswith("asset_render_setup"):
            del sys.modules[mod_name]


def _resolve_install_dir() -> str:
    """Find the install/ directory. Tries __file__ first, then asks the user."""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass

    cmds.confirmDialog(
        title="Asset Render Setup - Install",
        message=(
            "Maya cannot detect the script location automatically.\n\n"
            "In the next dialog, navigate to the install/ folder\n"
            "and select this same file: install.py"
        ),
        button=["OK"],
    )
    result = cmds.fileDialog2(
        fileMode=1,
        caption="Select install.py",
        okCaption="Install",
        fileFilter="Python (*.py)",
    )
    if not result:
        raise RuntimeError("Installation cancelled.")

    picked = result[0]
    dirname = os.path.dirname(os.path.abspath(picked))
    parent = os.path.dirname(dirname)
    scripts_dir = os.path.join(parent, "scripts", "asset_render_setup")
    if not os.path.isfile(os.path.join(scripts_dir, "__init__.py")):
        raise RuntimeError(
            "Selected file does not look like Maya_AssetRenderSetup/install/install.py.\n"
            f"Expected to find: {scripts_dir}/__init__.py"
        )
    return dirname


def _shelf_image(tool_root: str) -> str:
    """Custom icon from assets/ if present, else Maya built-in."""
    custom = os.path.join(tool_root, "assets", "shelf_icon.png")
    if os.path.isfile(custom):
        return os.path.normpath(custom).replace("\\", "/")
    return "render.png"


def _shelf_command() -> str:
    """Shelf button: no paths stored, discovers tool at click time."""
    return """
import os, sys
import maya.cmds as cmds

def _valid(p):
    return p and os.path.isdir(p) and os.path.isfile(
        os.path.join(p, "asset_render_setup", "__init__.py")
    )

def _candidates():
    out = []
    k = "TA_assetRenderSetup_scriptsPath"
    if cmds.optionVar(exists=k):
        out.append(cmds.optionVar(q=k))
    root = os.environ.get("MAYA_ASSET_RENDER_SETUP", "")
    if root:
        out.append(os.path.join(root, "scripts"))
    us = cmds.internalVar(userScriptDir=True)
    out.append(os.path.join(us, "Maya_AssetRenderSetup", "scripts"))
    for entry in os.environ.get("MAYA_SCRIPT_PATH", "").split(os.pathsep):
        if not entry:
            continue
        for c in (
            entry,
            os.path.join(entry, "scripts"),
            os.path.join(entry, "Maya_AssetRenderSetup", "scripts"),
        ):
            out.append(c)
    return out

for _p in _candidates():
    if _valid(_p):
        if _p not in sys.path:
            sys.path.insert(0, _p)
        for _m in list(sys.modules):
            if _m.startswith("asset_render_setup"):
                del sys.modules[_m]
        import asset_render_setup
        asset_render_setup.show()
        break
else:
    cmds.confirmDialog(
        title="Asset Render Setup",
        message=(
            "Tool not found.\\n\\n"
            "Install: File > Open Script > install/install.py > Execute\\n"
            "Or copy the repo to Documents/maya/scripts/Maya_AssetRenderSetup/"
        ),
        button="OK",
    )
"""


def _is_our_button(command: str, label: str) -> bool:
    if label in SHELF_LABELS:
        return True
    cmd = command or ""
    return any(marker in cmd for marker in SHELF_CMD_MARKERS)


def _remove_old_buttons(parent: str = "Custom") -> int:
    """Delete previously-installed Asset Render shelf buttons."""
    if not cmds.shelfLayout(parent, exists=True):
        return 0
    children = cmds.shelfLayout(parent, query=True, childArray=True) or []
    removed = 0
    for child in children:
        if not cmds.shelfButton(child, exists=True):
            continue
        try:
            cmd = cmds.shelfButton(child, query=True, command=True) or ""
            label = cmds.shelfButton(child, query=True, label=True) or ""
        except RuntimeError:
            continue
        if _is_our_button(cmd, label):
            cmds.deleteUI(child)
            removed += 1
    return removed


def _save_all_shelves() -> bool:
    """Persist shelf layouts so buttons survive tab switches and restarts."""
    # MEL variable form — reliable across Maya versions (never call bare saveAllShelves).
    try:
        mel.eval(
            "global string $TA_assetRenderShelfTop;"
            "$TA_assetRenderShelfTop = $gShelfTopLevel;"
            "saveAllShelves $TA_assetRenderShelfTop;"
        )
        return True
    except RuntimeError:
        pass

    try:
        top = mel.eval("$tmpVar=$gShelfTopLevel")
        if isinstance(top, (list, tuple)):
            top = top[0] if top else ""
        if top and hasattr(cmds, "saveAllShelves"):
            cmds.saveAllShelves(top)
            return True
    except Exception:
        pass

    print(
        "Asset Render Setup: warning — could not save shelves to disk. "
        "The button is installed for this session; re-run install after restarting Maya if it disappears."
    )
    return False


def _register_scripts_path(scripts_dir: str) -> None:
    """Remember install location for this Maya profile."""
    normalized = os.path.normpath(os.path.abspath(scripts_dir)).replace("\\", "/")
    cmds.optionVar(stringValue=(OPTIONVAR_SCRIPTS, normalized))


def install_shelf_button(parent: str = "Custom", label: str = "Asset Render") -> None:
    """Install (or refresh) the shelf button. Idempotent."""
    _purge_stale_modules()

    install_dir = _resolve_install_dir()
    tool_root = os.path.dirname(install_dir)
    scripts = os.path.join(tool_root, "scripts")

    if not os.path.isfile(os.path.join(scripts, "asset_render_setup", "__init__.py")):
        raise RuntimeError(
            "Could not find scripts/asset_render_setup/ next to install/. "
            f"Tool root: {tool_root}"
        )

    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    _register_scripts_path(scripts)

    removed = _remove_old_buttons(parent)
    if removed:
        print(f"Asset Render Setup: removed {removed} old shelf button(s).")

    if not cmds.shelfLayout(parent, exists=True):
        print(f"Asset Render Setup: shelf '{parent}' not found, creating button on current shelf.")
        parent = mel.eval("$tmp = $gShelfTopLevel") + "|"
        current_tab = cmds.tabLayout(
            mel.eval("$tmp = $gShelfTopLevel"), query=True, selectTab=True,
        )
        parent = current_tab

    cmds.shelfButton(
        command=_shelf_command(),
        annotation="Asset Render Setup - Arnold preview rig + fast PNG",
        label=label,
        image=_shelf_image(tool_root),
        parent=parent,
    )
    shelves_saved = _save_all_shelves()

    print("=" * 60)
    print("Asset Render Setup: installed successfully.")
    print(f"  Shelf button:  '{label}' on '{parent}'")
    print(f"  Shelves saved: {'yes' if shelves_saved else 'no (see warning above)'}")
    print(f"  Tool root:     {tool_root}")
    print(f"  Scripts path:  {scripts}")
    print("  Click the button to open the UI.")
    print("=" * 60)


install_shelf_button()
