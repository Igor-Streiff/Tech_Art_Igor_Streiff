"""Arranque en Maya: path, preferencias y ayudas de escena.

Pensado para que cualquiera copie la carpeta de la tool a su PC, ejecute
`run_in_maya.py` o instale el shelf una vez, y trabaje con su propio rig abierto.
"""

from __future__ import annotations

import sys
from pathlib import Path

_OPTION_TOOL_ROOT = "rigRenamerToolRoot"
_OPTION_RIG = "rigRenamerRigRoot"
_OPTION_CHAR = "rigRenamerCharacter"
_OPTION_KEYS = (_OPTION_TOOL_ROOT, _OPTION_RIG, _OPTION_CHAR)
_ENV_TOOL_ROOT = "RIG_RENAMER_TOOL"
_SHELF_BUTTON = "rigRenamerShelfBtn"  # nombre legado; hoy detectamos por marker
_SHELF_LABEL = "Rig Renamer"
# Marcas estables para reconocer nuestro botón (en memoria y en shelf_*.mel).
_SHELF_CMD_MARKERS = ("RigRenamerShelf", "rig_renamer.maya_ui", "from rig_renamer")

_DEFAULT_CAMERAS = frozenset(
    {"persp", "top", "front", "side", "left", "right", "back"}
)
_LAUNCHER_NAMES = frozenset(
    {"install_maya.py", "run_in_maya.py", "uninstall_maya.py"}
)


def is_valid_tool_root(path: Path) -> bool:
    root = path.resolve()
    return (root / "rig_renamer.py").is_file() and (root / "rig_renamer").is_dir()


def root_from_script_path(script_path: str | Path) -> Path | None:
    path = Path(script_path).resolve()
    if path.is_file() and path.suffix.lower() == ".py":
        candidate = path.parent
        if is_valid_tool_root(candidate):
            return candidate
    if path.is_dir() and is_valid_tool_root(path):
        return path.resolve()
    return None


def parse_mod_root(mod_text: str) -> str | None:
    for line in mod_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("+ RigRenamer"):
            parts = stripped.split(maxsplit=3)
            if len(parts) >= 4:
                return parts[3]
    return None


def _mod_file_path() -> Path:
    import maya.cmds as cmds

    version = cmds.about(version=True)
    return Path.home() / "Documents" / "maya" / version / "modules" / "RigRenamer.mod"


def root_from_maya_mod() -> Path | None:
    mod_path = _mod_file_path()
    if not mod_path.is_file():
        return None
    mod_root = parse_mod_root(mod_path.read_text(encoding="utf-8"))
    if not mod_root:
        return None
    candidate = Path(mod_root)
    if is_valid_tool_root(candidate):
        return candidate.resolve()
    return None


def root_from_env() -> Path | None:
    import os

    raw = os.environ.get(_ENV_TOOL_ROOT, "").strip()
    if not raw:
        return None
    candidate = Path(raw)
    if is_valid_tool_root(candidate):
        return candidate.resolve()
    return None


def pick_tool_root_dialog() -> Path:
    import maya.cmds as cmds

    picked = cmds.fileDialog2(
        fileMode=3,
        caption="Seleccioná la carpeta RigRenamer_Tool",
        okCaption="Seleccionar",
    )
    if not picked:
        raise RuntimeError(
            "No se encontró RigRenamer_Tool. Usá File → Open Script → install_maya.py "
            "(no pegues el código en el editor) o elegí la carpeta en el diálogo."
        )
    root = Path(picked[0]).resolve()
    if not is_valid_tool_root(root):
        raise RuntimeError(
            f"La carpeta no contiene rig_renamer.py: {root}\n"
            "Elegí la carpeta raíz del proyecto (RigRenamer_Tool)."
        )
    return root


def resolve_tool_root(
    explicit: Path | str | None = None,
    *,
    script_path: str | Path | None = None,
    allow_dialog: bool = True,
) -> Path:
    """Ubica la carpeta de la tool sin depender de rutas hardcodeadas."""
    if explicit is not None:
        root = Path(explicit).resolve()
        if is_valid_tool_root(root):
            return root
        raise RuntimeError(f"Ruta inválida de Rig Renamer: {root}")

    if script_path is not None:
        found = root_from_script_path(script_path)
        if found is not None:
            return found

    import inspect

    for frame_info in inspect.stack()[1:]:
        caller_file = frame_info.frame.f_globals.get("__file__")
        if not caller_file:
            continue
        caller_path = Path(caller_file)
        if caller_path.name in _LAUNCHER_NAMES:
            found = root_from_script_path(caller_path)
            if found is not None:
                return found

    try:
        found = root_from_script_path(Path(__file__))
        if found is not None:
            return found
    except NameError:
        pass

    try:
        saved = load_tool_root()
        if saved is not None and is_valid_tool_root(saved):
            return saved
    except ImportError:
        pass

    from_env = root_from_env()
    if from_env is not None:
        return from_env

    try:
        from_mod = root_from_maya_mod()
        if from_mod is not None:
            return from_mod
    except ImportError:
        pass

    if allow_dialog:
        return pick_tool_root_dialog()

    raise RuntimeError(
        "No se pudo ubicar RigRenamer_Tool. Ejecutá install_maya.py con "
        "File → Open Script, o pasá la ruta explícita."
    )


def tool_root(start: Path | None = None) -> Path:
    """Raíz del proyecto (carpeta que contiene rig_renamer.py)."""
    if start is not None:
        return start.resolve()
    try:
        here = Path(__file__).resolve().parent.parent
        if is_valid_tool_root(here):
            return here
    except NameError:
        pass
    return resolve_tool_root(allow_dialog=False)


def ensure_on_path(root: Path | None = None) -> Path:
    root = root or tool_root()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def ensure_path(
    root: Path | None = None,
    *,
    script_path: str | Path | None = None,
    allow_dialog: bool = True,
) -> Path:
    """Asegura PYTHONPATH y devuelve la raíz de la tool."""
    if root is None:
        root = resolve_tool_root(script_path=script_path, allow_dialog=allow_dialog)
    return ensure_on_path(root)


def save_tool_root(root: Path) -> None:
    import maya.cmds as cmds

    cmds.optionVar(stringValue=(_OPTION_TOOL_ROOT, str(root.resolve())))


def load_tool_root() -> Path | None:
    import maya.cmds as cmds

    if not cmds.optionVar(exists=_OPTION_TOOL_ROOT):
        return None
    path = Path(cmds.optionVar(q=_OPTION_TOOL_ROOT))
    if path.is_dir():
        return path.resolve()
    return None


def load_ui_prefs() -> tuple[str, str]:
    import maya.cmds as cmds

    rig = cmds.optionVar(q=_OPTION_RIG) if cmds.optionVar(exists=_OPTION_RIG) else ""
    char = cmds.optionVar(q=_OPTION_CHAR) if cmds.optionVar(exists=_OPTION_CHAR) else ""
    return rig, char


def save_ui_prefs(rig_root: str, character: str) -> None:
    import maya.cmds as cmds

    cmds.optionVar(stringValue=(_OPTION_RIG, rig_root))
    cmds.optionVar(stringValue=(_OPTION_CHAR, character))


def filter_assembly_candidates(assemblies: list[str]) -> list[str]:
    return [name for name in assemblies if name.split("|")[-1] not in _DEFAULT_CAMERAS]


def pick_rig_candidate(candidates: list[str], descendant_counts: dict[str, int]) -> str:
    if not candidates:
        return ""
    if len(candidates) == 1:
        return candidates[0]
    return max(candidates, key=lambda name: descendant_counts.get(name, 0))


def guess_rig_root() -> str:
    """Sugerencia de top-group: selección → único assembly → el más grande."""
    import maya.cmds as cmds

    selection = cmds.ls(selection=True, transforms=True) or []
    if selection:
        return selection[0]

    candidates = filter_assembly_candidates(cmds.ls(assemblies=True, transforms=True) or [])
    counts = {
        name: len(cmds.listRelatives(name, allDescendents=True, type="transform") or [])
        for name in candidates
    }
    return pick_rig_candidate(candidates, counts)


def shelf_command_source() -> str:
    """Código del botón: NO guarda ruta; descubre la tool al hacer clic.

    Así el botón sigue funcionando aunque muevas la carpeta (mientras haya
    optionVar, env var o RigRenamer.mod válidos).
    """
    return (
        "# RigRenamerShelf\n"
        "import os, sys\n"
        "import maya.cmds as cmds\n"
        "\n"
        "def _valid(p):\n"
        "    return bool(p) and os.path.isfile(os.path.join(p, 'rig_renamer.py')) \\\n"
        "        and os.path.isdir(os.path.join(p, 'rig_renamer'))\n"
        "\n"
        "def _from_mod():\n"
        "    try:\n"
        "        ver = cmds.about(version=True)\n"
        "        mod = os.path.join(os.path.expanduser('~'), 'Documents', 'maya', ver,\n"
        "                           'modules', 'RigRenamer.mod')\n"
        "        if os.path.isfile(mod):\n"
        "            with open(mod, encoding='utf-8') as fh:\n"
        "                for line in fh:\n"
        "                    s = line.strip()\n"
        "                    if s.startswith('+ RigRenamer'):\n"
        "                        parts = s.split(None, 3)\n"
        "                        if len(parts) >= 4:\n"
        "                            return parts[3]\n"
        "    except Exception:\n"
        "        pass\n"
        "    return ''\n"
        "\n"
        "def _candidates():\n"
        "    out = []\n"
        "    if cmds.optionVar(exists='rigRenamerToolRoot'):\n"
        "        out.append(cmds.optionVar(q='rigRenamerToolRoot'))\n"
        "    out.append(os.environ.get('RIG_RENAMER_TOOL', ''))\n"
        "    out.append(_from_mod())\n"
        "    return out\n"
        "\n"
        "for _p in _candidates():\n"
        "    if _valid(_p):\n"
        "        if _p not in sys.path:\n"
        "            sys.path.insert(0, _p)\n"
        "        for _m in list(sys.modules):\n"
        "            if _m == 'rig_renamer' or _m.startswith('rig_renamer.') \\\n"
        "                    or _m == 'maya_kit' or _m.startswith('maya_kit.'):\n"
        "                del sys.modules[_m]\n"
        "        from rig_renamer.maya_ui import show\n"
        "        show()\n"
        "        break\n"
        "else:\n"
        "    cmds.confirmDialog(title='Rig Renamer', message=(\n"
        "        'No se encontro la tool.\\n\\nReinstala: arrastra '\n"
        "        'drag_to_install_maya.py a la vista 3D de Maya.'), button=['OK'])\n"
    )


def open_ui() -> None:
    ensure_path()
    from rig_renamer.maya_ui import show

    show()


def _purge_stale_modules() -> None:
    """Descarta versiones cacheadas para que reinstalar cargue código fresco."""
    for name in list(sys.modules):
        if (
            name in ("rig_renamer", "maya_kit")
            or name.startswith("rig_renamer.")
            or name.startswith("maya_kit.")
        ):
            del sys.modules[name]


def _save_all_shelves() -> bool:
    """Persiste los shelves en disco (sobrevive a cambios de pestaña / reinicio)."""
    import maya.cmds as cmds
    import maya.mel as mel

    try:
        mel.eval(
            "global string $rigRenamerShelfTop;"
            "$rigRenamerShelfTop = $gShelfTopLevel;"
            "saveAllShelves $rigRenamerShelfTop;"
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
    print("[rig_renamer] Aviso: no se pudieron guardar los shelves en disco.")
    return False


def _button_is_ours(command: str, label: str) -> bool:
    if label == _SHELF_LABEL:
        return True
    cmd = command or ""
    return any(marker in cmd for marker in _SHELF_CMD_MARKERS)


def _iter_shelf_tabs() -> list[str]:
    import maya.cmds as cmds
    import maya.mel as mel

    try:
        top = mel.eval("$tmp = $gShelfTopLevel")
        tabs = cmds.tabLayout(top, query=True, childArray=True) or []
    except Exception:
        tabs = []
    return tabs or ["Custom"]


def _remove_buttons_from_shelf(tab: str) -> int:
    import maya.cmds as cmds

    if not cmds.shelfLayout(tab, exists=True):
        return 0
    removed = 0
    for child in cmds.shelfLayout(tab, query=True, childArray=True) or []:
        if not cmds.shelfButton(child, exists=True):
            continue
        try:
            cmd = cmds.shelfButton(child, query=True, command=True) or ""
            label = cmds.shelfButton(child, query=True, label=True) or ""
        except RuntimeError:
            continue
        if _button_is_ours(cmd, label):
            cmds.deleteUI(child)
            removed += 1
    return removed


def _remove_buttons_all_shelves() -> int:
    import maya.cmds as cmds

    total = 0
    if cmds.control(_SHELF_BUTTON, exists=True):
        try:
            cmds.deleteUI(_SHELF_BUTTON)
            total += 1
        except RuntimeError:
            pass
    for tab in _iter_shelf_tabs():
        total += _remove_buttons_from_shelf(tab)
    return total


def install_shelf(*, shelf: str | None = None) -> str:
    """Crea (o refresca) el botón del shelf. Idempotente."""
    import maya.cmds as cmds

    _purge_stale_modules()
    root = ensure_path()
    save_tool_root(root)

    removed = _remove_buttons_all_shelves()
    if removed:
        print(f"[rig_renamer] Botones previos removidos: {removed}")

    target_shelf = shelf
    if not target_shelf:
        import maya.mel as mel

        target_shelf = cmds.tabLayout(
            mel.eval("$tmp = $gShelfTopLevel"), query=True, selectTab=True
        )
    if not cmds.shelfLayout(target_shelf, exists=True):
        print(f"[rig_renamer] Shelf '{target_shelf}' no existe; uso 'Custom'.")
        target_shelf = "Custom"

    cmds.shelfButton(
        parent=target_shelf,
        label=_SHELF_LABEL,
        imageOverlayLabel="Rename",
        image="pythonFamily.png",
        command=shelf_command_source(),
        annotation="Abrir Rig Renamer (dry-run + renombrar controles)",
        sourceType="python",
    )
    saved = _save_all_shelves()
    print(f"[rig_renamer] Botón '{_SHELF_LABEL}' creado en '{target_shelf}'.")
    print(f"[rig_renamer] Shelves guardados: {'sí' if saved else 'no'}")
    return target_shelf


def install_module_file() -> Path:
    """Escribe RigRenamer.mod en ~/Documents/maya/<versión>/modules/."""
    root = ensure_path()
    save_tool_root(root)
    mod_path = _mod_file_path()
    mod_path.parent.mkdir(parents=True, exist_ok=True)
    mod_path.write_text(
        f"+ RigRenamer 1.0 {root}\nscripts: .\nPYTHONPATH+:=.\n",
        encoding="utf-8",
    )
    print(f"[rig_renamer] Módulo Maya escrito en: {mod_path}")
    print("[rig_renamer] Reiniciá Maya para cargarlo automáticamente en futuras sesiones.")
    return mod_path


def install_all(*, shelf: str | None = None) -> None:
    """Instalación recomendada: shelf ahora + .mod para próximas sesiones."""
    install_shelf(shelf=shelf)
    install_module_file()


# --- Desinstalación -------------------------------------------------------


def _is_our_shelf_button_block(block: str) -> bool:
    if f'-label "{_SHELF_LABEL}"' in block:
        return True
    return any(marker in block for marker in _SHELF_CMD_MARKERS)


def _strip_shelf_buttons_from_mel(text: str) -> tuple[str, int]:
    """Quita bloques `shelfButton ... ;` que sean nuestros. Función pura."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    removed = 0
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("shelfButton"):
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


def _shelves_directory() -> Path:
    import maya.cmds as cmds

    return Path(cmds.internalVar(userPrefDir=True)) / "shelves"


def _scrub_shelf_pref_files() -> list[tuple[str, int]]:
    shelves_dir = _shelves_directory()
    if not shelves_dir.is_dir():
        return []
    changed: list[tuple[str, int]] = []
    for path in sorted(shelves_dir.glob("shelf_*.mel")):
        try:
            original = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        updated, count = _strip_shelf_buttons_from_mel(original)
        if count == 0:
            continue
        try:
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed.append((str(path), count))
        except OSError:
            continue
    return changed


def remove_module_file() -> Path | None:
    mod_path = _mod_file_path()
    if not mod_path.is_file():
        return None
    try:
        mod_path.unlink()
        return mod_path
    except OSError:
        return None


def remove_optionvars() -> list[str]:
    import maya.cmds as cmds

    removed: list[str] = []
    for key in _OPTION_KEYS:
        if cmds.optionVar(exists=key):
            cmds.optionVar(remove=key)
            removed.append(key)
    return removed


def uninstall_all(*, confirm: bool = True, scrub_prefs: bool = True) -> None:
    """Quita botón de shelf, .mod y optionVars. No borra la carpeta ni la escena."""
    import maya.cmds as cmds

    present = [k for k in _OPTION_KEYS if cmds.optionVar(exists=k)]
    root = cmds.optionVar(q=_OPTION_TOOL_ROOT) if cmds.optionVar(exists=_OPTION_TOOL_ROOT) else ""

    if confirm:
        msg = (
            "Rig Renamer — desinstalar\n\n"
            f"Ruta registrada: {root or '(ninguna)'}\n"
            f"optionVars: {', '.join(present) or '(ninguna)'}\n\n"
            "Quitar botón del shelf, módulo .mod y preferencias?\n"
            "No borra la carpeta de la tool ni nodos de la escena."
        )
        choice = cmds.confirmDialog(
            title="Desinstalar Rig Renamer",
            message=msg,
            button=["Desinstalar", "Cancelar"],
            defaultButton="Desinstalar",
            cancelButton="Cancelar",
            dismissString="Cancelar",
        )
        if choice != "Desinstalar":
            print("[rig_renamer] Desinstalación cancelada.")
            return

    removed_ui = _remove_buttons_all_shelves()
    _save_all_shelves()
    scrubbed = _scrub_shelf_pref_files() if scrub_prefs else []
    mod = remove_module_file()
    removed_vars = remove_optionvars()

    print("=" * 60)
    print("[rig_renamer] Desinstalado.")
    print(f"  Botones removidos (sesión): {removed_ui}")
    for path, count in scrubbed:
        print(f"  Editado {path} ({count} bloque(s) removido(s)).")
    if mod:
        print(f"  .mod borrado: {mod}")
    if removed_vars:
        print(f"  optionVars removidas: {', '.join(removed_vars)}")
    else:
        print("  No había optionVars.")
    print("  La carpeta de la tool NO se borró.")
    print("  Reinstalar: arrastrá drag_to_install_maya.py a la vista 3D de Maya.")
    print("=" * 60)
