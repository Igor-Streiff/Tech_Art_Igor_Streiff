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
    for node in sel:
        short = short_name(node)
        if is_rig_node(short):
            continue
        if cmds.nodeType(node) == "mesh":
            parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
            if parents:
                short = short_name(parents[0])
        if cmds.nodeType(short) == "transform" and cmds.objExists(short):
            if short not in result:
                result.append(short)
    return result


def _targets_from_scene() -> list[str]:
    result: list[str] = []
    meshes = cmds.ls(type="mesh", long=True) or []
    for mesh in meshes:
        if cmds.getAttr(f"{mesh}.intermediateObject"):
            continue
        parents = cmds.listRelatives(mesh, parent=True, fullPath=False) or []
        if not parents:
            continue
        xf = short_name(parents[0])
        if is_rig_node(xf) or xf in DEFAULT_CAMERAS:
            continue
        if not cmds.getAttr(f"{xf}.visibility"):
            continue
        if xf not in result:
            result.append(xf)
    return result


def compute_bbox(targets: list[str]) -> BBox:
    if not targets:
        raise ValueError("No mesh geometry found. Select your asset or add meshes to the scene.")
    bb = cmds.exactWorldBoundingBox(*targets)
    return BBox(
        min_x=bb[0],
        min_y=bb[1],
        min_z=bb[2],
        max_x=bb[3],
        max_y=bb[4],
        max_z=bb[5],
    )
