"""Desinstalar Rig Renamer de este perfil de Maya.

IMPORTANTE — cómo ejecutar (elegí UNA):

  A) File → Open Script → este archivo → Execute (▶)     ← recomendado
  B) Pegar SOLO esta línea en Script Editor (con tu ruta):

     import runpy; runpy.run_path(r"C:/ruta/a/RigRenamer_Tool/uninstall_maya.py", run_name="__main__")

  C) Si pegaste todo el archivo y falló: se abrirá un diálogo para elegir la carpeta.

Quita: botón del shelf (todas las pestañas), RigRenamer.mod y optionVars.
NO borra: la carpeta de la tool ni nodos de tu escena.
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
        if caller_file and Path(caller_file).name == "uninstall_maya.py":
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
            raise RuntimeError("Desinstalación cancelada.")
        root = Path(picked[0]).resolve()
        if not _is_valid_root(root):
            raise RuntimeError(f"No es RigRenamer_Tool: {root}")

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def uninstall(*, confirm: bool = True) -> None:
    _bootstrap_path()
    from rig_renamer.maya_bootstrap import uninstall_all

    uninstall_all(confirm=confirm)


if __name__ == "__main__":
    uninstall()
