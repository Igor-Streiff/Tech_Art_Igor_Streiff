"""Lógica pura del renamer: planificar, validar y resumir."""

from __future__ import annotations

from dataclasses import dataclass, field

from rig_renamer.conventions import DEFAULT_TARGET_TYPES
from rig_renamer.naming import propose_name
from rig_renamer.validate import (
    detect_foreign_character_prefix,
    is_canonical_for_character,
    normalize_character,
)


@dataclass(frozen=True)
class RenameSummary:
    found: int
    planned: int
    skipped: int
    collisions: list[str]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def safe_to_apply(self) -> bool:
        return self.planned > 0 and not self.collisions and not self.blockers


def build_rename_plan(
    node_names: list[str],
    character: str,
    target_types: frozenset[str] = DEFAULT_TARGET_TYPES,
) -> tuple[dict[str, str], RenameSummary]:
    """Arma el mapa old → new en RAM sin tocar la escena."""
    char = normalize_character(character)
    plan: dict[str, str] = {}
    skipped = 0
    collisions: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    proposed_targets: dict[str, str] = {}
    seen_foreign: set[str] = set()

    for full_name in node_names:
        short = full_name.rsplit("|", maxsplit=1)[-1]

        foreign = detect_foreign_character_prefix(short, char)
        if foreign and foreign not in seen_foreign:
            seen_foreign.add(foreign)
            blockers.append(
                f"Prefijo ajeno detectado: '{foreign}' en nombres como '{short}'. "
                f"La escena parece renombrada con otro personaje. "
                f"Reabrí la copia limpia/messy antes de aplicar con '{char}'."
            )

        if is_canonical_for_character(short, char):
            skipped += 1
            continue

        proposed = propose_name(char, short, target_types=target_types)
        if proposed is None:
            skipped += 1
            continue
        if proposed == short:
            skipped += 1
            continue

        if proposed in proposed_targets and proposed_targets[proposed] != full_name:
            collisions.append(
                f"Colisión: '{proposed}' desde '{proposed_targets[proposed]}' y '{full_name}'"
            )
            continue

        proposed_targets[proposed] = full_name
        plan[full_name] = proposed

    if not plan and not blockers and not collisions:
        warnings.append(
            "No hay renombres pendientes. ¿La escena ya está normalizada con este prefijo?"
        )

    summary = RenameSummary(
        found=len(node_names),
        planned=len(plan),
        skipped=skipped,
        collisions=collisions,
        blockers=blockers,
        warnings=warnings,
    )
    return plan, summary
