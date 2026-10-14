"""Abrir Rig Renamer en Maya — sin rutas absolutas ni PYTHONPATH manual.

IMPORTANTE — cómo ejecutar (elegí UNA):

  A) File → Open Script → este archivo → Execute (▶)     ← recomendado
  B) Botón Rig Renamer en el shelf (tras install_maya.py)
  C) Pegar SOLO esta línea en Script Editor:

     import runpy; runpy.run_path(r"C:/ruta/a/RigRenamer_Tool/run_in_maya.py", run_name="__main__")

Requisito: mantener la carpeta RigRenamer_Tool completa (no copies solo este .py).
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


def _is_valid_root(path: Path) -> bool:
    return (path / "rig_renamer.py").is_file() and (path / "rig_renamer").is_dir()


def _bootstrap_path() -> Path:
    script_path: str | None = None
    for frame_info in inspect.stack():
        caller_file = frame_info.frame.f_globals.get("__file__")
        if caller_file and Path(caller_file).name == "run_in_maya.py":
            script_path = caller_file
            break

    candidates: list[Path] = []
    if script_path:
        candidates.append(Path(script_path).resolve().parent)
    try:
        candidates.append(Path(__file__).resolve().parent)
    except NameError:
        pass

    for candidate in candidates:
        if _is_valid_root(candidate):
            root = candidate
            break
    else:
        import maya.cmds as cmds

        picked = cmds.fileDialog2(
            fileMode=3,
            caption="Seleccioná la carpeta RigRenamer_Tool",
            okCaption="Seleccionar",
        )
        if not picked:
            raise RuntimeError("Apertura cancelada.")
        root = Path(picked[0]).resolve()
        if not _is_valid_root(root):
            raise RuntimeError(f"No es RigRenamer_Tool: {root}")

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def main() -> None:
    _bootstrap_path()
    from rig_renamer.maya_bootstrap import open_ui

    open_ui()


if __name__ == "__main__":
    main()
