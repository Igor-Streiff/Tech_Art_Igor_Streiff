"""Resolve tool location without hardcoded paths (optionVar, env, Maya folders, package)."""

from __future__ import annotations

import os
import sys

OPTIONVAR_SCRIPTS = "TA_assetRenderSetup_scriptsPath"
ENV_TOOL_ROOT = "MAYA_ASSET_RENDER_SETUP"
USER_SCRIPTS_SUBDIR = os.path.join("Maya_AssetRenderSetup", "scripts")
PACKAGE_DIR = "asset_render_setup"


def _is_valid_scripts_dir(path: str) -> bool:
    if not path or not os.path.isdir(path):
        return False
    return os.path.isfile(os.path.join(path, PACKAGE_DIR, "__init__.py"))


def _norm(path: str) -> str:
    return os.path.normpath(path).replace("\\", "/")


def register_scripts_dir(scripts_dir: str) -> str:
    """Remember install location for this Maya profile."""
    scripts_dir = _norm(os.path.abspath(scripts_dir))
    if not _is_valid_scripts_dir(scripts_dir):
        raise ValueError(
            f"Invalid scripts folder (expected {PACKAGE_DIR}/): {scripts_dir}"
        )
    try:
        import maya.cmds as cmds

        cmds.optionVar(stringValue=(OPTIONVAR_SCRIPTS, scripts_dir))
    except ImportError:
        pass
    return scripts_dir


def tool_root() -> str:
    """Maya_AssetRenderSetup folder (parent of scripts/)."""
    return os.path.dirname(resolve_scripts_dir())


def _from_package() -> str | None:
    scripts = _norm(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    return scripts if _is_valid_scripts_dir(scripts) else None


def _from_optionvar() -> str | None:
    try:
        import maya.cmds as cmds

        if cmds.optionVar(exists=OPTIONVAR_SCRIPTS):
            path = cmds.optionVar(query=OPTIONVAR_SCRIPTS) or ""
            if _is_valid_scripts_dir(path):
                return _norm(path)
    except ImportError:
        pass
    return None


def _from_env() -> str | None:
    raw = os.environ.get(ENV_TOOL_ROOT, "").strip()
    if not raw:
        return None
    raw = os.path.abspath(raw)
    candidates = [
        raw,
        os.path.join(raw, "scripts"),
        os.path.join(raw, "Maya_AssetRenderSetup", "scripts"),
    ]
    for path in candidates:
        if _is_valid_scripts_dir(path):
            return _norm(path)
    return None


def _from_user_scripts() -> str | None:
    try:
        import maya.cmds as cmds

        base = cmds.internalVar(userScriptDir=True)
        path = os.path.join(base, USER_SCRIPTS_SUBDIR)
        if _is_valid_scripts_dir(path):
            return _norm(path)
    except ImportError:
        pass
    return None


def _from_maya_script_path() -> str | None:
    for entry in os.environ.get("MAYA_SCRIPT_PATH", "").split(os.pathsep):
        entry = entry.strip()
        if not entry:
            continue
        candidates = (
            entry,
            os.path.join(entry, "scripts"),
            os.path.join(entry, "Maya_AssetRenderSetup", "scripts"),
        )
        for path in candidates:
            if _is_valid_scripts_dir(path):
                return _norm(path)
    return None


def iter_scripts_candidates() -> list[str]:
    """All known locations, in priority order (first match wins)."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(path: str | None) -> None:
        if not path or path in seen:
            return
        seen.add(path)
        ordered.append(path)

    add(_from_optionvar())
    add(_from_env())
    add(_from_user_scripts())
    add(_from_maya_script_path())
    add(_from_package())
    return ordered


def resolve_scripts_dir(*, register: bool = False) -> str:
    for path in iter_scripts_candidates():
        if register:
            register_scripts_dir(path)
        return path
    raise RuntimeError(
        "Asset Render Setup not found. Install once:\n"
        "  • Maya: File → Open Script → install/install.py → Execute\n"
        "  • Or copy this repo to [user]/maya/scripts/Maya_AssetRenderSetup/\n"
        f"  • Or set env {ENV_TOOL_ROOT} to the tool folder"
    )


def ensure_on_path() -> str:
    scripts_dir = resolve_scripts_dir()
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    return scripts_dir


def resolve_tool_root_from_path(path: str) -> str:
    """
    Accept tool root, scripts/, install/, or install/install.py.
    Returns absolute tool root (parent of scripts/).
    """
    path = os.path.abspath(path)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    name = os.path.basename(path).lower()
    if name == "install":
        path = os.path.dirname(path)
    elif name == "scripts":
        path = os.path.dirname(path)
    scripts = os.path.join(path, "scripts")
    if not _is_valid_scripts_dir(scripts):
        raise ValueError(f"Not a Maya_AssetRenderSetup folder: {path}")
    return path
