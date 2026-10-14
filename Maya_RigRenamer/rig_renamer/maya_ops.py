"""Operaciones que requieren Maya (cmds)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import maya.cmds as cmds  # type: ignore[import-not-found]


def _cmds():
    import maya.cmds as cmds_module

    return cmds_module


@dataclass
class ApplyResult:
    applied: dict[str, str] = field(default_factory=dict)
    failed: list[str] = field(default_factory=list)
    target_conflicts: list[str] = field(default_factory=list)
    new_orphans: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed and not self.target_conflicts and not self.new_orphans


def collect_descendant_transforms(rig_root: str) -> list[str]:
    """Lista transforms bajo el top-group del rig."""
    cmds = _cmds()
    if not cmds.objExists(rig_root):
        raise ValueError(f"No existe el nodo rig: {rig_root}")

    transforms = cmds.listRelatives(
        rig_root,
        allDescendents=True,
        type="transform",
        fullPath=False,
    ) or []
    nodes = sorted(set(transforms + [rig_root]))
    return nodes


def find_target_conflicts(plan: dict[str, str]) -> list[str]:
    """Detecta si un nombre destino ya existe en escena en otro nodo."""
    cmds = _cmds()
    conflicts: list[str] = []
    sources_becoming = {new for new in plan.values()}

    for old_name, new_short in plan.items():
        old_short = old_name.rsplit("|", maxsplit=1)[-1]
        if old_short == new_short:
            continue
        if not cmds.objExists(new_short):
            continue
        if new_short in sources_becoming:
            continue
        conflicts.append(
            f"El nombre '{new_short}' ya existe en escena (bloquea renombrar '{old_short}')"
        )
    return conflicts


def apply_rename_plan(plan: dict[str, str], logger: logging.Logger) -> ApplyResult:
    """Renombra nodos con cmds.rename. No aplica si hay conflictos previos."""
    cmds = _cmds()
    result = ApplyResult()

    result.target_conflicts = find_target_conflicts(plan)
    if result.target_conflicts:
        for message in result.target_conflicts:
            logger.error(message)
        return result

    orphans_before = set(find_orphan_animation_curves())

    for old_name, new_short in plan.items():
        if not cmds.objExists(old_name):
            message = f"Nodo no encontrado, se aborta el lote: {old_name}"
            logger.error(message)
            result.failed.append(message)
            break

        try:
            renamed = cmds.rename(old_name, new_short)
            result.applied[old_name] = renamed
            logger.info("RENAMED %s -> %s", old_name, renamed)
        except RuntimeError as exc:
            message = f"Fallo al renombrar {old_name} -> {new_short}: {exc}"
            logger.error(message)
            result.failed.append(message)
            break

    orphans_after = set(find_orphan_animation_curves())
    result.new_orphans = sorted(orphans_after - orphans_before)
    if result.new_orphans:
        for curve in result.new_orphans:
            logger.warning("Curva huérfana nueva: %s", curve)

    return result


def find_orphan_animation_curves() -> list[str]:
    """Curvas de animación sin conexiones de salida (huérfanas)."""
    cmds = _cmds()
    orphans: list[str] = []
    curves = cmds.ls(type="animCurve") or []

    for curve in curves:
        destinations = cmds.listConnections(curve, source=False, destination=True) or []
        if not destinations:
            orphans.append(curve)

    return orphans
