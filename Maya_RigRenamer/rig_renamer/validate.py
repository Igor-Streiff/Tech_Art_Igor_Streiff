"""Validación de entradas y nombres antes de planificar o aplicar."""

from __future__ import annotations

import re

_CHARACTER_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
_CANONICAL_SHAPE_RE = re.compile(
    r"^([a-zA-Z][a-zA-Z0-9_]*)_([LRC])_(.+)_([A-Z]{2,4})$"
)


def normalize_character(character: str) -> str:
    """Normaliza el prefijo del personaje (minúsculas, sin espacios)."""
    return character.strip().lower()


def validate_character(character: str) -> None:
    """Lanza ValueError si el prefijo no es válido para nombres Maya."""
    normalized = normalize_character(character)
    if not normalized:
        raise ValueError("El prefijo del personaje no puede estar vacío.")
    if not _CHARACTER_RE.match(normalized):
        raise ValueError(
            f"Prefijo inválido '{character}'. "
            "Usá solo letras, números y guión bajo; debe empezar con letra."
        )


def detect_foreign_character_prefix(short_name: str, character: str) -> str | None:
    """Si el nombre ya parece canónico de OTRO personaje, devuelve ese prefijo."""
    match = _CANONICAL_SHAPE_RE.match(short_name)
    if not match:
        return None
    embedded = match.group(1)
    if embedded.lower() == normalize_character(character):
        return None
    return embedded


def is_canonical_for_character(short_name: str, character: str) -> bool:
    """True si el nombre ya coincide con el formato canónico de este personaje."""
    from rig_renamer.naming import propose_name

    char = normalize_character(character)
    proposed = propose_name(char, short_name)
    if proposed is None:
        return False
    return proposed == short_name
