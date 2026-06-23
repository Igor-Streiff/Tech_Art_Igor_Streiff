"""Bounding box helpers."""

from __future__ import annotations

import maya.cmds as cmds

from .config import BBox, RIG_GRP, RIG_PREFIX


DEFAULT_CAMERAS = {"front", "persp", "side", "top"}


def short_name(node: str) -> str:
    if "|" in node:
        return node.rsplit("|", 1)[-1]
    return node


def is_rig_node(name: str) -> bool:
    short = short_name(name)
    if short == RIG_GRP:
        return True
    return short.startswith(RIG_PREFIX)


def _transform_visible(xf: str) -> bool:
    try:
        return bool(cmds.getAttr(f"{xf}.visibility"))
    except RuntimeError:
        return True


def _mesh_has_renderable_shape(mesh: str) -> bool:
    try:
        return not cmds.getAttr(f"{mesh}.intermediateObject")
    except RuntimeError:
        return True


def _add_mesh_targets_from_node(node: str, result: list[str], seen: set[str]) -> None:
    """Collect visible mesh transforms under *node* (selection may be a group)."""
    long_names = cmds.ls(node, long=True) or [node]
    node = long_names[0]

    if cmds.nodeType(node) == "mesh":
        parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
        if not parents:
            return
        node = parents[0]

    short = short_name(node)
    if is_rig_node(short) or short in DEFAULT_CAMERAS:
        return

    mesh_shapes = cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or []
    if mesh_shapes:
        if not _transform_visible(node):
            return
        if any(_mesh_has_renderable_shape(sh) for sh in mesh_shapes):
            if short not in seen:
                seen.add(short)
                result.append(short)
        return

    for mesh in cmds.listRelatives(node, allDescendents=True, type="mesh", fullPath=True) or []:
        if not _mesh_has_renderable_shape(mesh):
            continue
        parents = cmds.listRelatives(mesh, parent=True, fullPath=False) or []
        if not parents:
            continue
        xf = short_name(parents[0])
        if is_rig_node(xf) or xf in DEFAULT_CAMERAS:
            continue
        if not _transform_visible(parents[0]):
            continue
        if xf not in seen:
            seen.add(xf)
            result.append(xf)


def get_targets() -> list[str]:
    """Selection if any valid asset targets, else all visible mesh transforms."""
    sel = cmds.ls(selection=True, long=True) or []
    if sel:
        from_selection = _targets_from_selection(sel)
        if from_selection:
            return from_selection
    return _targets_from_scene()


def _targets_from_selection(sel: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for node in sel:
        if is_rig_node(short_name(node)):
            continue
        _add_mesh_targets_from_node(node, result, seen)
    return result


def _targets_from_scene() -> list[str]:
    result: list[str] = []
    meshes = cmds.ls(type="mesh", long=True) or []
    for mesh in meshes:
        if not _mesh_has_renderable_shape(mesh):
            continue
        parents = cmds.listRelatives(mesh, parent=True, fullPath=False) or []
        if not parents:
            continue
        xf = short_name(parents[0])
        if is_rig_node(xf) or xf in DEFAULT_CAMERAS:
            continue
        if not _transform_visible(parents[0]):
            continue
        if xf not in result:
            result.append(xf)
    return result


def _mesh_shapes_for_targets(targets: list[str]) -> list[str]:
    shapes: list[str] = []
    seen: set[str] = set()
    for xf in targets:
        if not cmds.objExists(xf):
            continue
        for mesh in cmds.listRelatives(xf, shapes=True, type="mesh", fullPath=True) or []:
            if not _mesh_has_renderable_shape(mesh):
                continue
            if mesh not in seen:
                seen.add(mesh)
                shapes.append(mesh)
    return shapes


def compute_bbox(targets: list[str]) -> BBox:
    if not targets:
        raise ValueError("No mesh geometry found. Select your asset or add meshes to the scene.")
    shapes = _mesh_shapes_for_targets(targets)
    nodes = shapes if shapes else targets
    bb = cmds.exactWorldBoundingBox(*nodes)
    return BBox(
        min_x=bb[0],
        min_y=bb[1],
        min_z=bb[2],
        max_x=bb[3],
        max_y=bb[4],
        max_z=bb[5],
    )
