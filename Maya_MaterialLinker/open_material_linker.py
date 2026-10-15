"""Open Material Linker. Keep the Maya_MaterialLinker folder intact.

Drag this file into Maya's viewport, or use Script Editor > File > Open Script.
"""
from pathlib import Path
import sys


def _valid_root(path):
    return (path / 'scripts' / 'material_linker' / 'ui.py').is_file()


def _root():
    script = globals().get('__file__')
    if script:
        candidate = Path(script).resolve().parent
        if _valid_root(candidate):
            return candidate
    import maya.cmds as cmds
    found = set()
    for editor in cmds.lsUI(type='cmdScrollFieldExecuter') or []:
        filename = cmds.cmdScrollFieldExecuter(editor, q=True, filename=True)
        if filename and Path(filename).name == 'open_material_linker.py':
            candidate = Path(filename).resolve().parent
            if _valid_root(candidate):
                found.add(candidate)
    if len(found) == 1:
        return found.pop()
    selected = cmds.fileDialog2(fileMode=3, caption='Select Maya_MaterialLinker folder', okCaption='Select')
    if not selected:
        return None
    candidate = Path(selected[0]).resolve()
    if not _valid_root(candidate):
        cmds.warning('Select the complete Maya_MaterialLinker folder containing scripts/material_linker.')
        return None
    return candidate


def main():
    root = _root()
    if root is None:
        return None
    scripts = str(root / 'scripts')
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from material_linker.ui import show
    return show()


def onMayaDroppedPythonFile(*_):
    return main() is not None


if __name__ == '__main__':
    main()
