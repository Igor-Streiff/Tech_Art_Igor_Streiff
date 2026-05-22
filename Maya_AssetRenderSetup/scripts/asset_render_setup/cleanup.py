"""Remove existing render rig nodes."""

from __future__ import annotations

import maya.cmds as cmds

from .config import RIG_GRP, RIG_PREFIX


def cleanup_rig() -> None:
    if cmds.objExists(RIG_GRP):
        cmds.delete(RIG_GRP)
    for orphan in ("bend1", "bend1Handle", "bend2", "bend2Handle"):
        if cmds.objExists(orphan):
            cmds.delete(orphan)
    patterns = (f"{RIG_PREFIX}*", "TA_assetRender_aim*", "TA_assetRender_cyc_profile")
    seen: set[str] = set()
    to_delete: list[str] = []
    for pattern in patterns:
        for node in cmds.ls(pattern) or []:
            if node not in seen and cmds.objExists(node):
                seen.add(node)
                to_delete.append(node)
    if to_delete:
        cmds.delete(to_delete)
