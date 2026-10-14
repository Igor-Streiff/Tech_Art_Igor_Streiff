"""Orquestación compartida entre CLI y UI Maya."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from rig_renamer.conventions import DEFAULT_TARGET_TYPES
from rig_renamer.core import RenameSummary, build_rename_plan
from rig_renamer.display import format_rename_table
from rig_renamer.validate import normalize_character, validate_character


@dataclass
class RunResult:
    summary: RenameSummary
    table: str
    display_plan: dict[str, str] = field(default_factory=dict)
    plan: dict[str, str] = field(default_factory=dict)
    apply_result: object | None = None
    exit_code: int = 0
    messages: list[str] = field(default_factory=list)


def _format_header(dry_run: bool, summary: RenameSummary) -> str:
    return (
        f"Modo: {'DRY-RUN' if dry_run else 'APPLY'}\n"
        f"Revisados={summary.found} | planificados={summary.planned} | "
        f"omitidos={summary.skipped}\n\n"
    )


def _format_footer(summary: RenameSummary, apply_result=None) -> str:
    parts: list[str] = []
    if summary.warnings:
        parts.append("ADVERTENCIAS:\n" + "\n".join(f"  - {w}" for w in summary.warnings))
    if summary.blockers:
        parts.append("BLOQUEADO:\n" + "\n".join(f"  - {b}" for b in summary.blockers))
    if summary.collisions:
        parts.append("COLISIONES:\n" + "\n".join(f"  - {c}" for c in summary.collisions))
    if apply_result is not None:
        parts.append(f"\nAplicados: {len(apply_result.applied)}")
        if apply_result.target_conflicts:
            parts.append(
                "Conflictos de destino:\n"
                + "\n".join(f"  - {c}" for c in apply_result.target_conflicts)
            )
        if apply_result.failed:
            parts.append("Fallos:\n" + "\n".join(f"  - {f}" for f in apply_result.failed))
        if apply_result.new_orphans:
            parts.append(f"Curvas huérfanas nuevas: {len(apply_result.new_orphans)}")
            for curve in apply_result.new_orphans[:5]:
                parts.append(f"  - {curve}")
        elif apply_result.ok:
            parts.append("Sin curvas huérfanas nuevas.")
    return "\n".join(parts)


def run_rename(
    node_names: list[str],
    character: str,
    *,
    dry_run: bool,
    logger: logging.Logger,
    target_types=DEFAULT_TARGET_TYPES,
    maya_ops=None,
) -> RunResult:
    """Planifica y opcionalmente aplica. Devuelve resultado estructurado."""
    try:
        validate_character(character)
    except ValueError as exc:
        return RunResult(
            summary=RenameSummary(found=0, planned=0, skipped=0, collisions=[]),
            table=str(exc),
            exit_code=1,
            messages=[str(exc)],
        )

    char = normalize_character(character)
    plan, summary = build_rename_plan(node_names, char, target_types=target_types)
    display_plan = {old.rsplit("|", 1)[-1]: new for old, new in plan.items()}
    table = format_rename_table(display_plan)
    header = _format_header(dry_run, summary)

    logger.info("Modo: %s", "DRY-RUN" if dry_run else "APPLY")
    logger.info("Prefijo normalizado: %s", char)
    logger.info(
        "Nodos revisados=%s | planificados=%s | omitidos=%s",
        summary.found,
        summary.planned,
        summary.skipped,
    )

    for warning in summary.warnings:
        logger.warning(warning)
    for blocker in summary.blockers:
        logger.error(blocker)
    for collision in summary.collisions:
        logger.warning(collision)

    result = RunResult(
        summary=summary,
        table=table,
        display_plan=display_plan,
        plan=plan,
    )

    if not summary.safe_to_apply:
        footer = _format_footer(summary)
        result.messages.append(footer)
        result.exit_code = 1
        if dry_run and summary.planned == 0 and not summary.blockers and not summary.collisions:
            result.exit_code = 0
        return result

    if dry_run:
        result.exit_code = 0
        return result

    if maya_ops is None:
        result.messages.append("Maya no disponible para apply.")
        result.exit_code = 1
        return result

    apply_result = maya_ops.apply_rename_plan(plan, logger)
    result.apply_result = apply_result
    footer = _format_footer(summary, apply_result)
    result.messages.append(footer)
    result.exit_code = 0 if apply_result.ok else 1
    return result


def format_run_output(result: RunResult, *, dry_run: bool) -> str:
    header = _format_header(dry_run, result.summary)
    body = result.table
    footer = "\n".join(result.messages)
    if footer:
        return f"{header}{body}\n\n{footer}"
    return f"{header}{body}"
