"""Tabla legible para dry-run."""

from __future__ import annotations


def format_rename_table(plan: dict[str, str]) -> str:
    """Genera una tabla old → new alineada con texto plano."""
    if not plan:
        return "No hay renombres pendientes."

    headers = ("OLD", "NEW")
    rows = [headers] + [(old, new) for old, new in sorted(plan.items())]
    widths = [
        max(len(row[index]) for row in rows)
        for index in range(2)
    ]

    lines: list[str] = []
    separator = f"+-{'-' * widths[0]}-+-{'-' * widths[1]}-+"
    lines.append(separator)
    lines.append(
        f"| {headers[0]:<{widths[0]}} | {headers[1]:<{widths[1]}} |"
    )
    lines.append(separator)

    for old, new in rows[1:]:
        lines.append(f"| {old:<{widths[0]}} | {new:<{widths[1]}} |")

    lines.append(separator)
    lines.append(f"Total: {len(plan)} renombres")
    return "\n".join(lines)
