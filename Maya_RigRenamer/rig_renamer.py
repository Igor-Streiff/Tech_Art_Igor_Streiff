#!/usr/bin/env python3
"""CLI del Rig Renamer — dry-run por default, --apply para ejecutar en Maya."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rig_renamer.conventions import DEFAULT_TARGET_TYPES, KNOWN_TYPES
from rig_renamer.core import build_rename_plan
from rig_renamer.display import format_rename_table
from rig_renamer.logger_setup import setup_logger


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normaliza nombres de controles de rig en Maya "
            "al formato <personaje>_<lado>_<parte>_<sufijo>."
        )
    )
    parser.add_argument(
        "--rig",
        help="Top-group del rig en la escena Maya (ej: hero:root_grp).",
    )
    parser.add_argument(
        "--character",
        required=True,
        help="Prefijo del personaje (ej: hero).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta el renombrado en la escena. Sin este flag = dry-run.",
    )
    parser.add_argument(
        "--include-joints",
        action="store_true",
        help="Además de controles, renombra joints (sufijo JNT).",
    )
    parser.add_argument(
        "--types",
        help=(
            "Lista de tipos a renombrar separados por coma (ej: CTL,JNT,GRP). "
            f"Tipos válidos: {','.join(sorted(KNOWN_TYPES))}. "
            "Anula --include-joints."
        ),
    )
    parser.add_argument(
        "--sample",
        type=Path,
        help="Archivo JSON con lista de nombres para probar sin Maya.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "logs",
        help="Carpeta donde guardar logs.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Más detalle en consola.",
    )
    return parser.parse_args()


def _load_sample_names(sample_path: Path) -> list[str]:
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("El sample JSON debe ser una lista de strings.")
    return [str(item) for item in data]


def _resolve_target_types(args: argparse.Namespace) -> frozenset[str]:
    if args.types:
        requested = {chunk.strip().upper() for chunk in args.types.split(",") if chunk.strip()}
        unknown = requested - KNOWN_TYPES
        if unknown:
            raise ValueError(
                f"Tipos no reconocidos: {', '.join(sorted(unknown))}. "
                f"Válidos: {', '.join(sorted(KNOWN_TYPES))}."
            )
        return frozenset(requested)

    types = set(DEFAULT_TARGET_TYPES)
    if args.include_joints:
        types.add("JNT")
    return frozenset(types)


def _run_in_maya(
    rig_root: str,
    character: str,
    apply: bool,
    target_types: frozenset[str],
    logger,
) -> int:
    try:
        from rig_renamer import maya_ops
        from rig_renamer.runner import format_run_output, run_rename
    except ImportError as exc:
        logger.error("Maya no disponible: %s", exc)
        return 1

    try:
        nodes = maya_ops.collect_descendant_transforms(rig_root)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    result = run_rename(
        nodes,
        character,
        dry_run=not apply,
        logger=logger,
        target_types=target_types,
        maya_ops=maya_ops if apply else None,
    )
    output = format_run_output(result, dry_run=not apply)
    print(output)
    logger.info("\n%s", output)
    return result.exit_code


def _run_offline(
    sample_path: Path,
    character: str,
    target_types: frozenset[str],
    logger,
) -> int:
    try:
        names = _load_sample_names(sample_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.error("No se pudo leer sample: %s", exc)
        return 1

    plan, summary = build_rename_plan(names, character, target_types=target_types)
    logger.info("Modo: OFFLINE SAMPLE (dry-run)")
    logger.info("Tipos objetivo: %s", ", ".join(sorted(target_types)))
    logger.info(
        "Nombres revisados=%s | planificados=%s | omitidos=%s",
        summary.found,
        summary.planned,
        summary.skipped,
    )

    for collision in summary.collisions:
        logger.warning(collision)

    table = format_rename_table(plan)
    print(table)
    logger.info("\n%s", table)
    return 1 if summary.collisions else 0


def main() -> int:
    args = _parse_args()
    logger = setup_logger(args.log_dir, verbose=args.verbose)

    try:
        target_types = _resolve_target_types(args)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    if args.sample:
        return _run_offline(args.sample, args.character, target_types, logger)

    if not args.rig:
        logger.error("Indica --rig para Maya o --sample para prueba offline.")
        return 1

    return _run_in_maya(args.rig, args.character, args.apply, target_types, logger)


if __name__ == "__main__":
    sys.exit(main())
