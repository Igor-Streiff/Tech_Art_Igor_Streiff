"""Punto de entrada en Maya — reexporta el bootstrap y helpers de demo.

Uso normal (cualquier rig, cualquier PC):
    Ejecutá run_in_maya.py desde Script Editor, o install_maya.py una vez.

Uso avanzado (demo con escena messy preconfigurada — solo curso):
    open_messy_and_ui("jinx")
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from rig_renamer.maya_bootstrap import ensure_path, open_ui

__all__ = ["ensure_path", "open_ui", "open_messy_and_ui", "rebuild_messy_and_ui"]


def open_messy_and_ui(kit_name: str) -> str:
    """Abre la escena messy del kit indicado + ventana (helper de demo)."""
    ensure_path()
    from maya_kit.kits import get_kit

    return get_kit(kit_name).open_messy_scene(open_ui_after=True)


def rebuild_messy_and_ui(kit_name: str) -> str:
    """Regenera la escena messy del kit + ventana (helper de demo)."""
    ensure_path()
    from maya_kit.kits import get_kit

    return get_kit(kit_name).build_messy_scene_from_clean(open_ui_after=True)
