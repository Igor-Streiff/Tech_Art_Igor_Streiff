"""UI mínima en Maya: rig + personaje → dry-run / apply."""

from __future__ import annotations

from pathlib import Path

import maya.cmds as cmds

from rig_renamer.conventions import DEFAULT_TARGET_TYPES
from rig_renamer.maya_bootstrap import guess_rig_root, load_ui_prefs, save_ui_prefs
from rig_renamer.runner import format_run_output, run_rename
from rig_renamer.logger_setup import setup_logger
from rig_renamer import maya_ops
from rig_renamer.validate import validate_character

_WINDOW = "rigRenamerWin"
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def _selected_rig_root() -> str:
    selection = cmds.ls(selection=True, transforms=True) or []
    return selection[0] if selection else ""


def _read_fields() -> tuple[str, str]:
    rig_root = cmds.textField(_WINDOW + "_rig", query=True, text=True).strip()
    character = cmds.textField(_WINDOW + "_char", query=True, text=True).strip()
    return rig_root, character


def _set_output(text: str) -> None:
    cmds.scrollField(_WINDOW + "_out", edit=True, text=text)


def _validate_inputs(rig_root: str, character: str) -> str | None:
    if not rig_root:
        return "Indicá el top-group del rig."
    if not character.strip():
        return "Indicá el prefijo del personaje."
    try:
        validate_character(character)
    except ValueError as exc:
        return str(exc)
    if not cmds.objExists(rig_root):
        return f"No existe el nodo: {rig_root}"
    return None


def _run(dry_run: bool) -> None:
    rig_root, character = _read_fields()
    error = _validate_inputs(rig_root, character)
    if error:
        cmds.warning(error)
        _set_output(error)
        return

    save_ui_prefs(rig_root, character)

    logger = setup_logger(_LOG_DIR, verbose=False)
    try:
        nodes = maya_ops.collect_descendant_transforms(rig_root)
    except ValueError as exc:
        _set_output(str(exc))
        return

    result = run_rename(
        nodes,
        character,
        dry_run=dry_run,
        logger=logger,
        target_types=DEFAULT_TARGET_TYPES,
        maya_ops=maya_ops if not dry_run else None,
    )
    output = format_run_output(result, dry_run=dry_run)
    _set_output(output)

    if result.exit_code != 0:
        cmds.warning("Operación con errores o bloqueada. Revisá Resultado y logs/.")
        return

    if dry_run:
        cmds.inViewMessage(
            amg=f"<hl>Rig Renamer</hl>: {result.summary.planned} renombres planificados",
            pos="topCenter",
            fade=True,
        )
        return

    cmds.inViewMessage(
        amg=f"<hl>Rig Renamer</hl>: {len(result.apply_result.applied)} controles renombrados",
        pos="topCenter",
        fade=True,
    )


def show() -> None:
    """Abre la ventana del renamer."""
    if cmds.window(_WINDOW, exists=True):
        cmds.deleteUI(_WINDOW)

    default_rig = _selected_rig_root() or guess_rig_root()
    saved_rig, saved_char = load_ui_prefs()
    if not default_rig and saved_rig:
        default_rig = saved_rig
    default_char = saved_char

    cmds.window(_WINDOW, title="Rig Renamer", sizeable=True, widthHeight=(640, 600))

    form = cmds.formLayout(numberOfDivisions=100)

    help_line = cmds.text(
        label="Abrí tu escena → top-group del rig + prefijo → Dry-run → RENOMBRAR",
        align="left",
        font="smallPlainLabelFont",
    )
    rig_label = cmds.text(label="Top-group del rig", align="left", font="boldLabelFont")
    rig_field = cmds.textField(_WINDOW + "_rig", text=default_rig, placeholderText="Group")
    char_label = cmds.text(label="Prefijo personaje", align="left", font="boldLabelFont")
    char_field = cmds.textField(_WINDOW + "_char", text=default_char, placeholderText="jinx")

    btn_row = cmds.rowLayout(
        numberOfColumns=3,
        adjustableColumn=1,
        columnAttach=[(1, "both", 0), (2, "both", 4), (3, "both", 0)],
    )
    cmds.button(
        label="Usar selección",
        command=lambda *_: cmds.textField(
            _WINDOW + "_rig", edit=True, text=_selected_rig_root() or guess_rig_root()
        ),
    )
    cmds.button(label="Dry-run", width=90, command=lambda *_: _run(dry_run=True))
    cmds.button(label="RENOMBRAR", width=110, command=lambda *_: _run(dry_run=False))
    cmds.setParent("..")

    out_label = cmds.text(label="Resultado", align="left", font="boldLabelFont")
    out_field = cmds.scrollField(
        _WINDOW + "_out",
        editable=False,
        wordWrap=False,
        font="fixedWidthFont",
    )

    pad = 12
    gap = 6
    cmds.formLayout(
        form,
        edit=True,
        attachForm=[
            (help_line, "top", pad),
            (help_line, "left", pad),
            (help_line, "right", pad),
            (rig_label, "left", pad),
            (rig_label, "right", pad),
            (rig_field, "left", pad),
            (rig_field, "right", pad),
            (char_label, "left", pad),
            (char_label, "right", pad),
            (char_field, "left", pad),
            (char_field, "right", pad),
            (btn_row, "left", pad),
            (btn_row, "right", pad),
            (out_label, "left", pad),
            (out_label, "right", pad),
            (out_field, "left", pad),
            (out_field, "right", pad),
            (out_field, "bottom", pad),
        ],
        attachControl=[
            (rig_label, "top", gap, help_line),
            (rig_field, "top", gap, rig_label),
            (char_label, "top", gap + 4, rig_field),
            (char_field, "top", gap, char_label),
            (btn_row, "top", gap + 6, char_field),
            (out_label, "top", gap + 8, btn_row),
            (out_field, "top", gap, out_label),
        ],
    )

    cmds.showWindow(_WINDOW)
