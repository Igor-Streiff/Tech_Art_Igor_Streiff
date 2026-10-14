"""DESINSTALADOR — arrastrá este archivo a la vista 3D de Maya.

Quita el botón "Rig Renamer" del shelf, el módulo RigRenamer.mod y las
preferencias guardadas. NO borra la carpeta de la tool ni nodos de tu escena.

Al soltar el archivo en el viewport, Maya define `__file__` y llama a
`onMayaDroppedPythonFile`, así que detecta su ruta sin diálogos.
"""

from __future__ import annotations

import os
import sys

_TOOL_ROOT = os.path.dirname(os.path.abspath(__file__))


def _uninstall(root: str) -> None:
    if not os.path.isfile(os.path.join(root, "rig_renamer.py")):
        raise RuntimeError(
            "Este archivo debe vivir dentro de RigRenamer_Tool "
            f"(no se encontró rig_renamer.py en: {root})."
        )
    if root not in sys.path:
        sys.path.insert(0, root)

    from rig_renamer.maya_bootstrap import uninstall_all

    uninstall_all()


def onMayaDroppedPythonFile(*_args, **_kwargs) -> None:
    """Maya llama a esta función al soltar el archivo en el viewport."""
    _uninstall(_TOOL_ROOT)


if __name__ == "__main__":
    _uninstall(_TOOL_ROOT)
