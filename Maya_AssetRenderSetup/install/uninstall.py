"""
Uninstall Asset Render Setup from this Maya profile.

Run from Maya:
  File -> Open Script -> select this file -> Execute

That's it. Auto-runs on load. If Maya can't detect the file location,
a dialog will ask you to point to this same uninstall.py file.

Removes:
  - Shelf button(s) for this tool (all shelf tabs)
  - Saved shelf .mel entries (so the button does not reappear)
  - optionVars: TA_assetRenderSetup_scriptsPath, TA_assetRenderSetup_outputDir

Does NOT delete:
  - The tool repository on disk
  - Scene nodes (TA_AssetRender_RIG) in open files
  - Optional copy under Documents/maya/.../scripts/Maya_AssetRenderSetup/
"""

from __future__ import annotations

import os
import re
import sys

import maya.cmds as cmds
import maya.mel as mel

OPTIONVAR_SCRIPTS = "TA_assetRenderSetup_scriptsPath"
OPTIONVAR_OUTPUT_DIR = "TA_assetRenderSetup_outputDir"
OPTIONVAR_KEYS = (OPTIONVAR_SCRIPTS, OPTIONVAR_OUTPUT_DIR)

SHELF_LABELS = ("Asset Render", "Asset Render Setup")
SHELF_CMD_MARKERS = (
    "TA_assetRenderSetup",
    "ta_shelf_launch",
    "asset_render_setup",
    "Maya_AssetRenderSetup",
)


def _resolve_install_dir() -> str:
    """Find the install/ directory. Tries __file__ first, then asks the user."""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass

    cmds.confirmDialog(
        title="Asset Render Setup - Uninstall",
        message=(
            "Maya cannot detect the script location automatically.\n\n"
            "In the next dialog, navigate to the install/ folder\n"
            "and select this same file: uninstall.py"
        ),
        button=["OK"],
    )
    result = cmds.fileDialog2(
        fileMode=1,
        caption="Select uninstall.py",
        okCaption="Uninstall",
        fileFilter="Python (*.py)",
    )
    if not result:
        raise RuntimeError("Uninstall cancelled.")

    picked = result[0]
    dirname = os.path.dirname(os.path.abspath(picked))
    parent = os.path.dirname(dirname)
    scripts_dir = os.path.join(parent, "scripts", "asset_render_setup")
    if not os.path.isfile(os.path.join(scripts_dir, "__init__.py")):
        raise RuntimeError(
            "Selected file does not look like Maya_AssetRenderSetup/install/uninstall.py.\n"
            f"Expected to find: {scripts_dir}/__init__.py"
        )
    return dirname


def _is_our_button(command: str, label: str) -> bool:
    if label in SHELF_LABELS:
        return True
    cmd = command or ""
    return any(marker in cmd for marker in SHELF_CMD_MARKERS)


def _remove_shelf_buttons(parent: str) -> int:
    """Delete matching shelf buttons on one shelf tab."""
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


def _remove_from_all_shelves() -> int:
    """Search every shelf tab for Asset Render buttons."""
    try:
        top = mel.eval("$tmp = $gShelfTopLevel")
        tabs = cmds.tabLayout(top, query=True, childArray=True) or []
    except Exception:
        tabs = ["Custom"]

    total = 0
    for tab in tabs:
        total += _remove_shelf_buttons(tab)
    if not total:
        total += _remove_shelf_buttons("Custom")
    return total


def _save_all_shelves() -> bool:
    """Persist shelf layouts (Maya requires the shelf top-level layout name)."""
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
        "Shelf .mel files were still scrubbed on disk where possible."
    )
    return False


def _get_optionvar_snapshot() -> dict[str, str]:
    out: dict[str, str] = {}
    for key in OPTIONVAR_KEYS:
        if cmds.optionVar(exists=key):
            out[key] = cmds.optionVar(query=key) or ""
    return out


def _remove_optionvars() -> list[str]:
    removed: list[str] = []
    for key in OPTIONVAR_KEYS:
        if cmds.optionVar(exists=key):
            cmds.optionVar(remove=key)
            removed.append(key)
    return removed


def _user_scripts_copy() -> str | None:
    try:
        base = cmds.internalVar(userScriptDir=True)
    except Exception:
        return None
    path = os.path.join(base, "Maya_AssetRenderSetup")
    return path if os.path.isdir(path) else None


def _shelves_directory() -> str:
    pref = cmds.internalVar(userPrefDir=True)
    return os.path.join(pref, "shelves")


def _is_our_shelf_button_block(block: str) -> bool:
    if any(f'-label "{label}"' in block for label in SHELF_LABELS):
        return True
    return any(marker in block for marker in SHELF_CMD_MARKERS)


def _strip_shelf_buttons_from_mel(text: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    removed = 0
    i = 0
    while i < len(lines):
        stripped = lines[i].lstrip()
        if stripped.startswith("shelfButton"):
            block: list[str] = []
            while i < len(lines):
                block.append(lines[i])
                if lines[i].strip() == ";":
                    i += 1
                    break
                i += 1
            if _is_our_shelf_button_block("".join(block)):
                removed += 1
                continue
            out.extend(block)
            continue
        out.append(lines[i])
        i += 1
    return "".join(out), removed


def _scrub_shelf_pref_files() -> list[tuple[str, int]]:
    shelves_dir = _shelves_directory()
    if not os.path.isdir(shelves_dir):
        return []

    changed: list[tuple[str, int]] = []
    for name in sorted(os.listdir(shelves_dir)):
        if not name.startswith("shelf_") or not name.endswith(".mel"):
            continue
        path = os.path.join(shelves_dir, name)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                original = fh.read()
        except OSError:
            continue
        updated, count = _strip_shelf_buttons_from_mel(original)
        if count == 0:
            continue
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(updated)
            changed.append((path, count))
        except OSError:
            continue
    return changed


def _scrub_optionvars_from_userprefs_mel() -> bool:
    pref = cmds.internalVar(userPrefDir=True)
    path = os.path.join(pref, "userPrefs.mel")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return False

    keys = set(OPTIONVAR_KEYS)
    new_lines = [
        ln
        for ln in lines
        if not any(re.search(rf'-sv\s+"{re.escape(key)}"', ln) for key in keys)
    ]
    if len(new_lines) == len(lines):
        return False
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(new_lines)
    except OSError:
        return False
    return True


def _detect_installation() -> dict:
    scripts = None
    if cmds.optionVar(exists=OPTIONVAR_SCRIPTS):
        scripts = (cmds.optionVar(query=OPTIONVAR_SCRIPTS) or "").strip() or None
    tool_root = os.path.dirname(scripts) if scripts else None
    return {
        "optionvars": _get_optionvar_snapshot(),
        "registered_scripts": scripts,
        "tool_root": tool_root,
        "env_maya_asset_render_setup": (
            os.environ.get("MAYA_ASSET_RENDER_SETUP", "").strip() or None
        ),
        "user_scripts_copy": _user_scripts_copy(),
        "shelves_dir": _shelves_directory(),
    }


def uninstall(
    *,
    scrub_prefs_files: bool = True,
    confirm: bool = True,
) -> None:
    """Remove shelf UI and saved prefs for this tool."""
    _resolve_install_dir()  # validate location / dialog if needed

    info = _detect_installation()
    scripts = info.get("registered_scripts")
    tool_root = info.get("tool_root")

    summary_lines = ["Asset Render Setup — uninstall"]
    if info["optionvars"]:
        summary_lines.append("Registered preferences:")
        for key, val in info["optionvars"].items():
            summary_lines.append(f"  {key} = {val}")
    else:
        summary_lines.append("No optionVars found for this tool.")

    if scripts:
        summary_lines.append(f"Scripts path: {scripts}")
    if tool_root:
        summary_lines.append(f"Tool root: {tool_root}")
    if info.get("env_maya_asset_render_setup"):
        summary_lines.append(
            "Env MAYA_ASSET_RENDER_SETUP is set (remove manually in Windows if unused): "
            f"{info['env_maya_asset_render_setup']}"
        )
    if info.get("user_scripts_copy"):
        summary_lines.append(
            "Optional scripts copy exists (not auto-deleted): "
            f"{info['user_scripts_copy']}"
        )

    if confirm:
        msg = "\n".join(summary_lines) + "\n\nRemove shelf button(s) and saved prefs?"
        proceed = cmds.confirmDialog(
            title="Uninstall Asset Render Setup",
            message=msg,
            button=["Uninstall", "Cancel"],
            defaultButton="Uninstall",
            cancelButton="Cancel",
        )
        if proceed != "Uninstall":
            print("Asset Render Setup: uninstall cancelled.")
            return

    removed_ui = _remove_from_all_shelves()
    _save_all_shelves()

    removed_disk: list[tuple[str, int]] = []
    prefs_scrubbed = False
    if scrub_prefs_files:
        removed_disk = _scrub_shelf_pref_files()
        prefs_scrubbed = _scrub_optionvars_from_userprefs_mel()

    removed_vars = _remove_optionvars()

    print("=" * 60)
    print("Asset Render Setup: uninstalled successfully.")
    print(f"  Shelf buttons removed (session): {removed_ui}")
    print("  Shelves saved to disk (saveAllShelves).")
    for path, count in removed_disk:
        print(f"  Edited {path} ({count} button block(s) removed).")
    if prefs_scrubbed:
        print("  Cleaned optionVar lines from userPrefs.mel.")
    if removed_vars:
        print(f"  optionVars removed: {', '.join(removed_vars)}")
    else:
        print("  No optionVars were set.")
    print("  Repository on disk was NOT deleted.")
    print("  Re-install: File -> Open Script -> install/install.py -> Execute")
    print("=" * 60)


uninstall()
