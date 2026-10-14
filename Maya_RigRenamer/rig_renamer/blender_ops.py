"""Operaciones que requieren Blender (bpy).

Adaptador equivalente a `maya_ops.py`: el núcleo (`naming`, `core`, `display`)
es Python puro y se reutiliza tal cual; solo cambia esta capa de I/O con el DCC.

Ejecutar dentro de Blender (Scripting workspace) o con `blender --python`.
No se importa fuera de Blender (import diferido de `bpy`).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bpy  # type: ignore[import-not-found]


def _bpy():
    import bpy as bpy_module

    return bpy_module


def _get_armature(armature_name: str):
    bpy = _bpy()
    obj = bpy.data.objects.get(armature_name)
    if obj is None:
        raise ValueError(f"No existe el objeto: {armature_name}")
    if obj.type != "ARMATURE":
        raise ValueError(f"El objeto '{armature_name}' no es un armature.")
    return obj


def collect_bone_names(armature_name: str) -> list[str]:
    """Lista los nombres de huesos del armature (controles + deform)."""
    armature = _get_armature(armature_name)
    return sorted(bone.name for bone in armature.data.bones)


def collect_child_object_names(root_name: str) -> list[str]:
    """Lista nombres de objetos hijos (controles tipo Empty u objetos)."""
    bpy = _bpy()
    root = bpy.data.objects.get(root_name)
    if root is None:
        raise ValueError(f"No existe el objeto: {root_name}")
    names = [root.name]
    names.extend(child.name for child in root.children_recursive)
    return sorted(set(names))


def apply_bone_rename_plan(
    armature_name: str,
    plan: dict[str, str],
    logger: logging.Logger,
) -> dict[str, str]:
    """Renombra huesos en EDIT mode (Blender remapea fcurves/constraints/drivers).

    Aviso: los *vertex groups* del skin NO se renombran solos; usar el operador
    de Blender o renombrarlos en paralelo si el rig ya tiene skinning.
    """
    bpy = _bpy()
    armature = _get_armature(armature_name)
    applied: dict[str, str] = {}

    previous_mode = bpy.context.object.mode if bpy.context.object else "OBJECT"
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        edit_bones = armature.data.edit_bones
        for old_name, new_name in plan.items():
            bone = edit_bones.get(old_name)
            if bone is None:
                logger.error("Hueso no encontrado, se omite: %s", old_name)
                continue
            bone.name = new_name
            applied[old_name] = new_name
            logger.info("RENAMED bone %s -> %s", old_name, new_name)
    finally:
        bpy.ops.object.mode_set(mode=previous_mode)

    return applied


def apply_object_rename_plan(
    plan: dict[str, str],
    logger: logging.Logger,
) -> dict[str, str]:
    """Renombra objetos (Empties/controles) por nombre."""
    bpy = _bpy()
    applied: dict[str, str] = {}
    for old_name, new_name in plan.items():
        obj = bpy.data.objects.get(old_name)
        if obj is None:
            logger.error("Objeto no encontrado, se omite: %s", old_name)
            continue
        obj.name = new_name
        applied[old_name] = obj.name
        logger.info("RENAMED object %s -> %s", old_name, obj.name)
    return applied


def to_blender_symmetry_name(canonical: str) -> str:
    """Convierte `char_L_comp_..._TYPE` al estilo Blender `char_comp_..._TYPE.L`.

    Mueve el lado (segundo token) a un sufijo `.L`/`.R` para que funcionen las
    herramientas de simetría/Symmetrize de Blender. Center (`C`) se deja sin
    sufijo. Es opcional: el formato canónico con `_L_` también es válido.
    """
    tokens = canonical.split("_")
    if len(tokens) < 3 or tokens[1] not in {"L", "R", "C"}:
        return canonical
    side = tokens.pop(1)
    base = "_".join(tokens)
    if side == "C":
        return base
    return f"{base}.{side}"
