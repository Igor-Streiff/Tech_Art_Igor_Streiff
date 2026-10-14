"""Taxonomía de naming de rigs de personaje.

Basado en convenciones de industria recopiladas en docs/INVESTIGACION.md:
SeithCG, Ronald Fong, mGear ({side}_{component}_{description}_{index}_{type}),
Faceware/MetaHuman (facial), Gnomon (cuadrúpedos/alas), Blender, Tech-Artists.org.

El parser clasifica cada token de un nombre en una categoría y reconstruye el
nombre canónico. Las tablas son fáciles de extender por proyecto.

Formato canónico objetivo:
    <character>_<side>_<component>_<position(s)>_<descriptor(s)>_<index>_<TYPE>
Ejemplo:
    L_handFkCtrl  ->  hero_L_hand_fk_CTL
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SIDE — lado del cuerpo. Se normaliza a L / R / C (center).
# Incluye inglés, español y abreviaturas comunes / mal escritas.
# ---------------------------------------------------------------------------
SIDE_ALIASES: dict[str, str] = {
    # Left (inglés)
    "l": "L",
    "lf": "L",
    "lft": "L",
    "lt": "L",
    "left": "L",
    # Left (español)
    "izq": "L",
    "izqda": "L",
    "izda": "L",
    "izquierda": "L",
    "izquierdo": "L",
    # Right (inglés)
    "r": "R",
    "rt": "R",
    "rgt": "R",
    "rg": "R",
    "right": "R",
    # Right (español)
    "der": "R",
    "dcha": "R",
    "dch": "R",
    "dech": "R",
    "derecha": "R",
    "derecho": "R",
    # Center (inglés + español)
    "c": "C",
    "cn": "C",
    "cen": "C",
    "ctr": "C",
    "cntr": "C",
    "center": "C",
    "centre": "C",
    "centro": "C",
    "central": "C",
}

DEFAULT_SIDE = "C"

# ---------------------------------------------------------------------------
# TYPE — sufijo de tipo de nodo. Solo los de familia CONTROL se renombran
# por default; el resto sirve para DETECTAR y SALTAR (joints, geo, grupos).
# ---------------------------------------------------------------------------
CONTROL_TYPE_ALIASES: dict[str, str] = {
    "ctl": "CTL",
    "ctrl": "CTL",
    "ctrls": "CTL",
    "con": "CTL",
    "cnt": "CTL",
    "cont": "CTL",
    "control": "CTL",
    "anim": "CTL",
    "ani": "CTL",
    "handle": "CTL",
}

# Tipos NO-control: si un nodo termina así, se omite (no es un control).
NON_CONTROL_TYPE_ALIASES: dict[str, str] = {
    "jnt": "JNT",
    "jt": "JNT",
    "joint": "JNT",
    "bnd": "JNT",
    "bind": "JNT",
    "skn": "JNT",
    "def": "JNT",
    "end": "JNT",
    "grp": "GRP",
    "gp": "GRP",
    "group": "GRP",
    "grup": "GRP",
    "ofs": "GRP",
    "off": "GRP",
    "offset": "GRP",
    "srt": "GRP",
    "zero": "GRP",
    "zro": "GRP",
    "null": "GRP",
    "nul": "GRP",
    "loc": "LOC",
    "locator": "LOC",
    "geo": "GEO",
    "msh": "GEO",
    "mesh": "GEO",
    "geom": "GEO",
    "rndr": "GEO",
    "crv": "CRV",
    "ikh": "IKH",
    "ikhandle": "IKH",
    "clt": "CLT",
    "cluster": "CLT",
}

CANONICAL_CONTROL_TYPE = "CTL"

# Tipos que el renamer puede renombrar. Por default solo controles; el flag
# --include-joints agrega "JNT". --types permite elegir cualquiera de KNOWN_TYPES.
DEFAULT_TARGET_TYPES: frozenset[str] = frozenset({"CTL"})
KNOWN_TYPES: frozenset[str] = frozenset({"CTL"}) | frozenset(
    NON_CONTROL_TYPE_ALIASES.values()
)

# ---------------------------------------------------------------------------
# CONTROL HINTS — palabras que delatan un control aunque no tenga sufijo
# (típico en GUIs faciales / joysticks de intercambio de textura "anime").
# ---------------------------------------------------------------------------
CONTROL_HINTS: frozenset[str] = frozenset(
    {"joystick", "slider", "selector", "swap", "pad", "picker", "switch"}
)

# ---------------------------------------------------------------------------
# POSITION — modificadores de posición. Inglés + español + abreviaturas.
# ---------------------------------------------------------------------------
POSITION_ALIASES: dict[str, str] = {
    # vertical
    "up": "upper",
    "upr": "upper",
    "upper": "upper",
    "sup": "upper",
    "superior": "upper",
    "arriba": "upper",
    "lo": "lower",
    "lwr": "lower",
    "low": "lower",
    "lower": "lower",
    "dn": "lower",
    "down": "lower",
    "inf": "lower",
    "inferior": "lower",
    "abajo": "lower",
    "top": "top",
    "btm": "bottom",
    "bot": "bottom",
    "bottom": "bottom",
    # profundidad / antero-posterior (incluye delantero/trasero de cuadrúpedos)
    "fr": "front",
    "fnt": "front",
    "front": "front",
    "fore": "front",
    "frontal": "front",
    "frente": "front",
    "delante": "front",
    "delantero": "front",
    "anterior": "front",
    "bk": "back",
    "rear": "back",
    "back": "back",
    "hind": "back",
    "posterior": "back",
    "atras": "back",
    "detras": "back",
    "trasero": "back",
    # interior / exterior
    "in": "inner",
    "inn": "inner",
    "inner": "inner",
    "interior": "inner",
    "int": "inner",
    "out": "outer",
    "outer": "outer",
    "exterior": "outer",
    "ext": "outer",
    # medio
    "mid": "mid",
    "middle": "mid",
    "medio": "mid",
    # cadena de dedos / segmentos
    "prox": "proximal",
    "proximal": "proximal",
    "inter": "intermediate",
    "intermediate": "intermediate",
    "dist": "distal",
    "distal": "distal",
    "tip": "tip",
    "base": "base",
}

# ---------------------------------------------------------------------------
# DESCRIPTOR — rol / función del control. Incluye sistemas (fk/ik), helpers,
# conectores (plug/socket/attach/prop) y GUI facial (joystick/selector).
# ---------------------------------------------------------------------------
DESCRIPTOR_ALIASES: dict[str, str] = {
    # sistemas cinemáticos
    "fk": "fk",
    "ik": "ik",
    "fkik": "switch",
    "ikfk": "switch",
    "blend": "switch",
    "switch": "switch",
    "pole": "pole",
    "pv": "pole",
    "polevector": "pole",
    "upv": "pole",
    "upvector": "pole",
    # deformación / refinamiento
    "twist": "twist",
    "twst": "twist",
    "bend": "bend",
    "bendy": "bend",
    "tweak": "tweak",
    "tweaker": "tweak",
    "twk": "tweak",
    "micro": "tweak",
    "stretch": "stretch",
    "str": "stretch",
    "squash": "squash",
    "dyn": "dyn",
    "dynamic": "dyn",
    "dynamics": "dyn",
    # controles maestros / jerarquía global
    "master": "master",
    "main": "main",
    "global": "global",
    "world": "world",
    "cog": "cog",
    "root": "root",
    "god": "master",
    "all": "master",
    # espacios / follow / settings / gui
    "space": "space",
    "spc": "space",
    "spaceswitch": "space",
    "follow": "follow",
    "flw": "follow",
    "settings": "settings",
    "setting": "settings",
    "config": "settings",
    "options": "settings",
    "opt": "settings",
    "gui": "gui",
    "ui": "gui",
    "panel": "gui",
    "picker": "gui",
    "attr": "attr",
    "attribute": "attr",
    "holder": "attr",
    # conectores / props / anclajes
    "space_": "space",
    "socket": "socket",
    "skt": "socket",
    "attach": "attach",
    "atch": "attach",
    "plug": "plug",
    "connector": "connector",
    "connect": "connector",
    "conn": "connector",
    "cnx": "connector",
    "grip": "grip",
    "prop": "prop",
    "pickup": "pickup",
    "pick": "pickup",
    "weapon": "weapon",
    "wpn": "weapon",
    "anchor": "anchor",
    "pin": "pin",
    # GUI / facial joystick (incluye swap de textura estilo anime)
    "joystick": "joystick",
    "joy": "joystick",
    "stick": "joystick",
    "slider": "slider",
    "sldr": "slider",
    "pad": "pad",
    "selector": "selector",
    "select": "selector",
    "sel": "selector",
    "swap": "selector",
    "texswap": "selector",
    "textureswap": "selector",
    "aim": "aim",
    "look": "aim",
    "lookat": "aim",
}

# ---------------------------------------------------------------------------
# KNOWN_PARTS — catálogo de partes anatómicas reconocidas (biped, cuadrúpedo,
# alado, cola/tentáculo, cara). Solo para reporte/validación: cualquier token
# desconocido igual se conserva como parte para no perder cobertura.
# ---------------------------------------------------------------------------
KNOWN_PARTS: frozenset[str] = frozenset(
    {
        # tronco / cabeza
        "root", "cog", "hip", "hips", "pelvis", "spine", "chest", "torso",
        "neck", "head", "skull",
        # brazos / manos
        "clavicle", "scapula", "shoulder", "arm", "forearm", "elbow",
        "wrist", "hand", "palm",
        # dedos
        "finger", "thumb", "index", "middle", "ring", "pinky", "little",
        "metacarpal",
        # piernas / pies (biped)
        "leg", "thigh", "knee", "shin", "calf", "ankle", "foot", "heel",
        "toe", "ball", "upleg", "lowleg",
        # cuadrúpedo (front/hind se clasifican como posición, no como parte)
        "femur", "tibia", "hock", "tarsal", "metatarsal",
        "fetlock", "paw", "claw", "hoof", "haunch",
        # alas
        "wing", "feather", "patagium", "covert",
        # cola / tentáculo / apéndices
        "tail", "tentacle", "antenna", "whisker", "fin", "horn", "tongue",
        "ear", "trunk", "mandible",
        # cara
        "eye", "eyeball", "iris", "pupil", "lid", "eyelid", "brow",
        "eyebrow", "cheek", "jaw", "chin", "lip", "mouth", "corner",
        "nose", "nostril", "teeth", "tooth", "gum", "forehead", "temple",
        "face",
    }
)
