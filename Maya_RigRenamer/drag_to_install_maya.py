"""INSTALADOR — arrastrá este archivo a la vista 3D de Maya.

Cómo instalar (para cualquier usuario, en cualquier PC):
  1. Abrí Maya.
  2. Desde el explorador de archivos, arrastrá ESTE archivo
     (drag_to_install_maya.py) y solTALO sobre el viewport 3D de Maya.
  3. Listo: aparece el botón "Rig Renamer" en el shelf activo y se registra
     la tool para futuras sesiones.

Por qué así: cuando Maya recibe un archivo soltado en el viewport, ejecuta el
archivo REAL (define `__file__`) y llama a `onMayaDroppedPythonFile`. Por eso
detecta su propia ruta sin diálogos ni escribir rutas a mano.

Requisito: mantené la carpeta RigRenamer_Tool completa (no muevas solo este .py).
"""

from __future__ import annotations

import os
import sys

# Al soltar el archivo en el viewport, Maya define __file__ apuntando aquí.
_TOOL_ROOT = os.path.dirname(os.path.abspath(__file__))


def _install(root: str) -> None:
    if not os.path.isfile(os.path.join(root, "rig_renamer.py")):
        raise RuntimeError(
            "Este archivo debe vivir dentro de RigRenamer_Tool "
            f"(no se encontró rig_renamer.py en: {root})."
        )
    if root not in sys.path:
        sys.path.insert(0, root)

    from rig_renamer.maya_bootstrap import install_all

    install_all()
    print("[rig_renamer] Instalación completa. Buscá el botón 'Rig Renamer' en tu shelf.")


def onMayaDroppedPythonFile(*_args, **_kwargs) -> None:
    """Maya llama a esta función al soltar el archivo en el viewport."""
    _install(_TOOL_ROOT)


if __name__ == "__main__":
    _install(_TOOL_ROOT)
