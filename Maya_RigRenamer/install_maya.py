"""Instalación única en Maya: botón de shelf + módulo para futuras sesiones.

IMPORTANTE — cómo ejecutar (elegí UNA):

  A) File → Open Script → este archivo → Execute (▶)     ← recomendado
  B) Pegar SOLO esta línea en Script Editor (con tu ruta):

     import runpy; runpy.run_path(r"C:/ruta/a/RigRenamer_Tool/install_maya.py", run_name="__main__")

  C) Si pegaste todo el archivo y falló: se abrirá un diálogo para elegir la carpeta.

No copies y pegues todo el contenido del script en el editor: Maya no define __file__ ahí.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


def _bootstrap_path() -> Path:
    script_path: str | None = None
    for frame_info in inspect.stack():
        caller_file = frame_info.frame.f_globals.get("__file__")
        if caller_file and Path(caller_file).name == "install_maya.py":
            script_path = caller_file
            break

    # Primera pasada: ubicar root con stdlib + diálogo si hace falta.
    root: Path | None = None
    for candidate in _iter_root_candidates(script_path):
        if _is_valid_root(candidate):
            root = candidate
            break

    if root is None:
        import maya.cmds as cmds

        picked = cmds.fileDialog2(
            fileMode=3,
            caption="Seleccioná la carpeta RigRenamer_Tool",
            okCaption="Seleccionar",
        )
        if not picked:
            raise RuntimeError("Instalación cancelada.")
        root = Path(picked[0]).resolve()
        if not _is_valid_root(root):
            raise RuntimeError(f"No es RigRenamer_Tool: {root}")

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def _is_valid_root(path: Path) -> bool:
    return (path / "rig_renamer.py").is_file() and (path / "rig_renamer").is_dir()


def _iter_root_candidates(script_path: str | None):
    if script_path:
        yield Path(script_path).resolve().parent
    try:
        yield Path(__file__).resolve().parent
    except NameError:
        pass


def install_all(*, shelf: str | None = None) -> None:
    _bootstrap_path()
    from rig_renamer.maya_bootstrap import install_all as _install_all

    _install_all(shelf=shelf)


def install_shelf(*, shelf: str | None = None) -> str:
    _bootstrap_path()
    from rig_renamer.maya_bootstrap import install_shelf as _install_shelf

    return _install_shelf(shelf=shelf)


def install_module_file() -> Path:
    _bootstrap_path()
    from rig_renamer.maya_bootstrap import install_module_file as _install_module_file

    return _install_module_file()


if __name__ == "__main__":
    install_all()
