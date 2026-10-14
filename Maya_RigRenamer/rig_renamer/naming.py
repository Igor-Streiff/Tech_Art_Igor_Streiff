"""Parser y normalizador de nombres de controles de rig.

Clasifica cada token de un nombre (side / position / descriptor / index / part)
usando las tablas de `conventions.py` y reconstruye el nombre canónico:

    <character>_<side>_<component>_<position(s)>_<descriptor(s)>_<index>_<TYPE>
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rig_renamer.conventions import (
    CANONICAL_CONTROL_TYPE,
    CONTROL_HINTS,
    CONTROL_TYPE_ALIASES,
    DEFAULT_SIDE,
    DEFAULT_TARGET_TYPES,
    DESCRIPTOR_ALIASES,
    NON_CONTROL_TYPE_ALIASES,
    POSITION_ALIASES,
    SIDE_ALIASES,
)

_INDEX_RE = re.compile(r"^v?(\d+)$", re.IGNORECASE)
_SPLIT_RE = re.compile(r"[_\-.\s]+")
_CAMEL_1 = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_2 = re.compile(r"([A-Z]+)([A-Z][a-z])")

DEFAULT_INDEX_PADDING = 2


@dataclass(frozen=True)
class ParsedControl:
    """Componentes extraídos de un nombre de nodo de rig."""

    original: str
    side: str
    component: str
    positions: list[str] = field(default_factory=list)
    descriptors: list[str] = field(default_factory=list)
    index: str | None = None
    ctype: str | None = None

    @property
    def is_control(self) -> bool:
        return self.ctype == CANONICAL_CONTROL_TYPE


def _strip_namespace(name: str) -> str:
    """Quita namespace (`ns:`) y path DAG (`|...`), deja el nombre corto."""
    short = name.rsplit("|", maxsplit=1)[-1]
    return short.rsplit(":", maxsplit=1)[-1]


def _split_camel(token: str) -> list[str]:
    spaced = _CAMEL_1.sub(r"\1 \2", token)
    spaced = _CAMEL_2.sub(r"\1 \2", spaced)
    return spaced.split()


def _tokenize(text: str) -> list[str]:
    rough = _SPLIT_RE.split(text)
    tokens: list[str] = []
    for chunk in rough:
        if not chunk:
            continue
        tokens.extend(_split_camel(chunk))
    return [token for token in tokens if token]


def _detect_type(short: str) -> tuple[str, str | None]:
    """Devuelve (base_sin_sufijo, tipo_canónico).

    El tipo es None cuando el nombre no termina en un sufijo reconocido ni
    contiene un hint de control: en ese caso el nodo no se renombra.
    """
    tokens = _tokenize(short)
    if not tokens:
        return short, None

    last = tokens[-1].lower()

    if last in CONTROL_TYPE_ALIASES:
        base = short[: short.lower().rfind(last)].rstrip("_-. ")
        return base, CONTROL_TYPE_ALIASES[last]

    if last in NON_CONTROL_TYPE_ALIASES:
        base = short[: short.lower().rfind(last)].rstrip("_-. ")
        return base, NON_CONTROL_TYPE_ALIASES[last]

    lowered = {token.lower() for token in tokens}
    if lowered & CONTROL_HINTS:
        return short, CANONICAL_CONTROL_TYPE

    return short, None


def _normalize_index(raw: str, padding: int = DEFAULT_INDEX_PADDING) -> str:
    match = _INDEX_RE.match(raw)
    digits = match.group(1) if match else raw
    return str(int(digits)).zfill(padding)


def _classify(tokens: list[str], character: str | None) -> ParsedControl:
    side = DEFAULT_SIDE
    side_found = False
    positions: list[str] = []
    descriptors: list[str] = []
    index: str | None = None
    component_tokens: list[str] = []

    for raw in tokens:
        key = raw.lower()

        if character and key == character.lower():
            continue
        if _INDEX_RE.match(raw):
            index = _normalize_index(raw)
            continue
        if not side_found and key in SIDE_ALIASES:
            side = SIDE_ALIASES[key]
            side_found = True
            continue
        if key in POSITION_ALIASES:
            value = POSITION_ALIASES[key]
            if value not in positions:
                positions.append(value)
            continue
        if key in DESCRIPTOR_ALIASES:
            value = DESCRIPTOR_ALIASES[key]
            if value not in descriptors:
                descriptors.append(value)
            continue
        component_tokens.append(key)

    # Si no quedó ninguna parte anatómica, el primer descriptor pasa a ser el
    # componente (ej. cog_ctrl -> cog, weapon_socket_ctrl -> weapon + socket).
    if not component_tokens and descriptors:
        component_tokens = [descriptors[0]]
        descriptors = descriptors[1:]

    component = "_".join(component_tokens) if component_tokens else "control"

    return ParsedControl(
        original="_".join(tokens),
        side=side,
        component=component,
        positions=positions,
        descriptors=descriptors,
        index=index,
    )


def is_control_name(name: str) -> bool:
    """True si el nombre parece un control de animación."""
    _, ctype = _detect_type(_strip_namespace(name))
    return ctype == CANONICAL_CONTROL_TYPE


def parse_control_name(name: str, character: str | None = None) -> ParsedControl:
    """Divide un nombre en side / component / positions / descriptors / index."""
    short = _strip_namespace(name)
    base, ctype = _detect_type(short)
    tokens = _tokenize(base)
    parsed = _classify(tokens, character)

    return ParsedControl(
        original=short,
        side=parsed.side,
        component=parsed.component,
        positions=parsed.positions,
        descriptors=parsed.descriptors,
        index=parsed.index,
        ctype=ctype,
    )


from rig_renamer.validate import normalize_character


def build_canonical_name(character: str, parsed: ParsedControl) -> str:
    """Construye el nombre canónico a partir de las piezas parseadas."""
    char = normalize_character(character)

    chunks: list[str] = [char, parsed.side, parsed.component]
    chunks.extend(parsed.positions)
    chunks.extend(parsed.descriptors)
    if parsed.index:
        chunks.append(parsed.index)
    chunks.append(parsed.ctype or CANONICAL_CONTROL_TYPE)
    return "_".join(chunk for chunk in chunks if chunk)


def propose_name(
    character: str,
    node_name: str,
    target_types: frozenset[str] = DEFAULT_TARGET_TYPES,
) -> str | None:
    """Devuelve el nombre canónico, o None si el nodo no debe renombrarse.

    Solo se proponen nombres para nodos cuyo tipo detectado esté en
    `target_types` (por default {'CTL'}; agregá 'JNT' para incluir joints).
    """
    parsed = parse_control_name(node_name, character=character)
    if parsed.ctype is None or parsed.ctype not in target_types:
        return None
    return build_canonical_name(character, parsed)
