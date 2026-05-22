"""Build render rig (camera, lights, cyclorama, reference kit)."""

from __future__ import annotations

import maya.cmds as cmds

from . import bbox, config
from .config import BBox, LightingPreset, RigOptions


def _as_transform(result) -> str:
    """Maya 2027+ may return a single transform name instead of (transform, shape)."""
    if isinstance(result, (list, tuple)):
        return result[0]
    return result


def _safe_set(plug: str, value, attr_type: str | None = None) -> bool:
    """Set attribute, ignoring errors. Returns True if successful."""
    if not cmds.objExists(plug):
        return False
    try:
        connections = cmds.listConnections(plug, source=True, destination=False) or []
        if connections:
            return False
        if attr_type == "double3":
            cmds.setAttr(plug, value[0], value[1], value[2], type="double3")
        else:
            cmds.setAttr(plug, value)
        return True
    except Exception:
        return False


def _force_parent(node: str, parent: str) -> str:
    """Parent *node* under *parent* and return the resulting DAG path."""
    if not cmds.objExists(node) or not cmds.objExists(parent):
        return node
    current_parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    if current_parents and bbox.short_name(current_parents[0]) == bbox.short_name(parent):
        return node
    try:
        result = cmds.parent(node, parent)
        if result:
            return result[0]
    except RuntimeError:
        pass
    return node


def _force_rename(node: str, desired: str) -> str:
    """Rename *node* to *desired*. Returns final name (may include suffix on conflict)."""
    if bbox.short_name(node) == desired:
        return node
    renamed = cmds.rename(node, desired)
    if renamed != desired and renamed.endswith(("1", "2", "3", "4", "5", "6", "7", "8", "9")):
        for conflict in cmds.ls(desired, long=True) or []:
            if conflict != renamed and cmds.objExists(conflict):
                try:
                    cmds.delete(conflict)
                except RuntimeError:
                    continue
        renamed = cmds.rename(renamed, desired)
    return renamed


# ---------------------------------------------------------------------------
# Area lights
# ---------------------------------------------------------------------------

def _create_area_light(
    name: str,
    position: tuple[float, float, float],
    scale: tuple[float, float, float],
    exposure: float,
    aim_at: tuple[float, float, float],
    rig: str,
) -> str:
    transform = cmds.shadingNode("aiAreaLight", asLight=True, name=name)
    short = (cmds.ls(transform, shortNames=True) or [transform])[0]
    if short != name:
        transform = cmds.rename(transform, name)

    shapes = cmds.listRelatives(transform, shapes=True, fullPath=True) or []
    if not shapes:
        raise RuntimeError(f"No shape found for light {transform}")
    shape = shapes[0]

    if not _safe_set(f"{shape}.color", (1.0, 1.0, 1.0), "double3"):
        _safe_set(f"{shape}.colorR", 1.0)
        _safe_set(f"{shape}.colorG", 1.0)
        _safe_set(f"{shape}.colorB", 1.0)

    _safe_set(f"{shape}.intensity", 1.0)
    _safe_set(f"{shape}.exposure", exposure)
    _safe_set(f"{shape}.aiSamples", config.LIGHT_SAMPLES)
    if not _safe_set(f"{shape}.aiNormalize", 1):
        _safe_set(f"{shape}.normalize", 1)

    cmds.xform(transform, worldSpace=True, translation=position)
    cmds.xform(transform, worldSpace=True, scale=scale)

    tmp = cmds.spaceLocator(name="TA_assetRender_aimTmp")[0]
    cmds.xform(tmp, worldSpace=True, translation=aim_at)
    cmds.aimConstraint(
        tmp,
        transform,
        offset=(0, 0, 0),
        weight=1,
        aimVector=(0, 0, -1),
        upVector=(0, 1, 0),
        worldUpType="vector",
        worldUpVector=(0, 1, 0),
    )
    cmds.delete(tmp)

    transform = _force_parent(transform, rig)
    return transform


# ---------------------------------------------------------------------------
# Cameras
# ---------------------------------------------------------------------------

def _cleanup_camera(name: str) -> None:
    """Remove stale camera nodes whose short name matches *name* exactly."""
    for node in cmds.ls(f"{config.RIG_PREFIX}*", type="transform") or []:
        if node.rsplit("|", 1)[-1] == name:
            if cmds.objExists(node):
                cmds.delete(node)
    if cmds.objExists(name):
        cmds.delete(name)


def _create_single_camera(
    name: str,
    position: tuple[float, float, float],
    aim_at: tuple[float, float, float],
    rig: str,
) -> tuple[str, str]:
    """Create one camera aimed at a target point. Returns (transform, shape)."""
    _cleanup_camera(name)

    result = cmds.camera()
    default_transform = result[0] if isinstance(result, (list, tuple)) else result
    cam_transform = _force_rename(default_transform, name)

    shapes = cmds.listRelatives(cam_transform, shapes=True, fullPath=False) or []
    cam_shape = shapes[0] if shapes else None
    if cam_shape:
        cam_shape = _force_rename(cam_shape, f"{name}Shape")

    cmds.xform(cam_transform, worldSpace=True, translation=position)

    tmp = cmds.spaceLocator(name="TA_assetRender_aim_tmp")[0]
    cmds.xform(tmp, worldSpace=True, translation=aim_at)
    cmds.aimConstraint(
        tmp,
        cam_transform,
        offset=(0, 0, 0),
        weight=1,
        aimVector=(0, 0, -1),
        upVector=(0, 1, 0),
        worldUpType="vector",
        worldUpVector=(0, 1, 0),
    )
    cmds.delete(tmp)

    constraints = cmds.listRelatives(cam_transform, type="aimConstraint") or []
    for c in constraints:
        if cmds.objExists(c):
            cmds.delete(c)

    if cam_shape and cmds.objExists(f"{cam_shape}.focalLength"):
        cmds.setAttr(f"{cam_shape}.focalLength", config.CAM_FOCAL_LENGTH)
    cmds.setAttr(f"{cam_transform}.renderable", 1)

    cam_transform = _force_parent(cam_transform, rig)
    return cam_transform, cam_shape or ""


def _create_camera(bbox: BBox, dist: float, rig: str) -> str:
    """Single hero camera (3/4 view). Original v2 behavior."""
    cx, cy, cz = bbox.center
    position = (cx + dist * 0.3, cy + dist * 0.4, cz + dist * 1.2)
    cam_transform, _ = _create_single_camera(
        config.CAM_NAME, position, (cx, cy, cz), rig,
    )
    if cmds.objExists("persp.renderable"):
        cmds.setAttr("persp.renderable", 0)
    return cam_transform


def _create_tri_cam(
    bbox: BBox, dist: float, rig: str, targets: list[str],
) -> list[str]:
    """Three cameras (main / side / high) with viewFit framing."""
    cx, cy, cz = bbox.center

    specs: list[tuple[str, tuple[float, float, float]]] = [
        (config.CAM_NAME, (cx + dist * 0.3, cy + dist * 0.4, cz + dist * 1.2)),
        (config.CAM_SIDE_NAME, (cx + dist * 1.5, cy + dist * 0.3, cz)),
        (config.CAM_HIGH_NAME, (cx, cy + dist * 1.5, cz + dist * 0.8)),
    ]

    cameras: list[str] = []
    shapes: list[str] = []
    for cam_name, position in specs:
        cam_xf, cam_sh = _create_single_camera(
            cam_name, position, (cx, cy, cz), rig,
        )
        cameras.append(cam_xf)
        shapes.append(cam_sh)

    if cmds.objExists("persp.renderable"):
        cmds.setAttr("persp.renderable", 0)

    # viewFit each camera to asset targets (excludes cyc + rig nodes)
    if targets:
        valid = [t for t in targets if cmds.objExists(t)]
        if valid:
            cmds.select(valid, replace=True)
            for cam_sh in shapes:
                cmds.viewFit(cam_sh, fitFactor=0.8)
            cmds.select(clear=True)

    return cameras


# ---------------------------------------------------------------------------
# Reference kit (chrome + gray validation spheres)
# ---------------------------------------------------------------------------

def _assign_chrome_shader(mesh: str) -> None:
    mtl = cmds.shadingNode(
        "aiStandardSurface", asShader=True, name="TA_assetRender_chromeMtl",
    )
    _safe_set(f"{mtl}.baseColor", config.REF_CHROME_COLOR, "double3")
    _safe_set(f"{mtl}.base", 1.0)
    _safe_set(f"{mtl}.metalness", 1.0)
    _safe_set(f"{mtl}.specular", 1.0)
    _safe_set(f"{mtl}.specularRoughness", 0.0)
    sg = cmds.sets(
        renderable=True, noSurfaceShader=True, empty=True,
        name="TA_assetRender_chromeSG",
    )
    cmds.connectAttr(f"{mtl}.outColor", f"{sg}.surfaceShader", force=True)
    cmds.sets(mesh, forceElement=sg)


def _assign_gray_shader(mesh: str) -> None:
    v = config.REF_GRAY_VALUE
    mtl = cmds.shadingNode(
        "aiStandardSurface", asShader=True, name="TA_assetRender_grayMtl",
    )
    _safe_set(f"{mtl}.baseColor", (v, v, v), "double3")
    _safe_set(f"{mtl}.base", 1.0)
    _safe_set(f"{mtl}.metalness", 0.0)
    _safe_set(f"{mtl}.specular", 0.3)
    _safe_set(f"{mtl}.specularRoughness", 0.5)
    sg = cmds.sets(
        renderable=True, noSurfaceShader=True, empty=True,
        name="TA_assetRender_graySG",
    )
    cmds.connectAttr(f"{mtl}.outColor", f"{sg}.surfaceShader", force=True)
    cmds.sets(mesh, forceElement=sg)


def _create_reference_kit(bbox: BBox, size: float, rig: str) -> list[str]:
    """Chrome mirror sphere + 18% gray sphere for lighting / color validation."""
    cx, cy, cz = bbox.center
    radius = size * config.REF_SPHERE_SCALE_MULT
    gap = size * config.REF_GAP_MULT

    base_x = bbox.max_x + gap + radius
    base_y = bbox.min_y + radius
    base_z = cz

    chrome = cmds.polySphere(
        name=config.REF_CHROME_NAME,
        radius=radius,
        subdivisionsX=config.REF_SPHERE_SEGS,
        subdivisionsY=config.REF_SPHERE_SEGS,
    )[0]
    cmds.xform(chrome, worldSpace=True, translation=(base_x, base_y, base_z))
    _assign_chrome_shader(chrome)
    chrome = _force_parent(chrome, rig)

    gray_x = base_x + radius * 2.5
    gray = cmds.polySphere(
        name=config.REF_GRAY_NAME,
        radius=radius,
        subdivisionsX=config.REF_SPHERE_SEGS,
        subdivisionsY=config.REF_SPHERE_SEGS,
    )[0]
    cmds.xform(gray, worldSpace=True, translation=(gray_x, base_y, base_z))
    _assign_gray_shader(gray)
    gray = _force_parent(gray, rig)

    return [chrome, gray]


# ---------------------------------------------------------------------------
# Cyclorama
# ---------------------------------------------------------------------------

def _assign_cyc_shader(mesh: str) -> None:
    """Assign neutral matte Arnold shader to cyclorama."""
    mtl = cmds.shadingNode("aiStandardSurface", asShader=True, name="TA_assetRender_cycMtl")
    _safe_set(f"{mtl}.baseColor", config.CYC_COLOR, "double3")
    _safe_set(f"{mtl}.base", 1.0)
    _safe_set(f"{mtl}.specular", 0.0)
    _safe_set(f"{mtl}.specularRoughness", 1.0)
    _safe_set(f"{mtl}.metalness", 0.0)
    _safe_set(f"{mtl}.diffuseRoughness", 0.3)

    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="TA_assetRender_cycSG")
    cmds.connectAttr(f"{mtl}.outColor", f"{sg}.surfaceShader", force=True)
    cmds.sets(mesh, forceElement=sg)


def _create_cyclorama(bbox: BBox, size: float, rig: str) -> str:
    """Infinity cove (studio backdrop): single continuous surface built in WORLD coords."""
    import math

    cx = (bbox.min_x + bbox.max_x) * 0.5

    width = size * config.CYC_WIDTH_MULT
    floor_depth = size * config.CYC_FLOOR_DEPTH_MULT
    curve_radius = size * config.CYC_CURVE_RADIUS_MULT
    wall_height = size * config.CYC_WALL_HEIGHT_MULT
    segs_curve = config.CYC_SEGS_CURVE

    floor_y = bbox.min_y + size * config.CYC_FLOOR_Y_OFFSET_MULT
    wall_pad = size * config.CYC_WALL_BACK_PAD_MULT
    curve_start_z = bbox.min_z - wall_pad
    wall_z = curve_start_z - curve_radius
    floor_front_z = curve_start_z + floor_depth

    half_width = width / 2.0

    profile_pts: list[tuple[float, float, float]] = []
    profile_pts.append((0.0, floor_y, floor_front_z))
    profile_pts.append((0.0, floor_y, curve_start_z))

    for i in range(1, segs_curve):
        t = i / float(segs_curve)
        angle = (math.pi / 2.0) * t
        local_y = curve_radius * (1.0 - math.cos(angle))
        local_z = curve_radius * (1.0 - math.sin(angle))
        profile_pts.append((0.0, floor_y + local_y, wall_z + local_z))

    profile_pts.append((0.0, floor_y + curve_radius, wall_z))
    profile_pts.append((0.0, floor_y + curve_radius + wall_height, wall_z))

    left_pts = [(cx - half_width, p[1], p[2]) for p in profile_pts]
    right_pts = [(cx + half_width, p[1], p[2]) for p in profile_pts]

    try:
        left_curve = cmds.curve(d=3, p=left_pts, name="TA_cyc_left")
        right_curve = cmds.curve(d=3, p=right_pts, name="TA_cyc_right")
    except TypeError:
        import maya.mel as mel
        mel_left = ["curve", "-d", "3", "-n", "TA_cyc_left"]
        mel_right = ["curve", "-d", "3", "-n", "TA_cyc_right"]
        for lp, rp in zip(left_pts, right_pts):
            mel_left.extend(["-p", str(lp[0]), str(lp[1]), str(lp[2])])
            mel_right.extend(["-p", str(rp[0]), str(rp[1]), str(rp[2])])
        left_curve = mel.eval(" ".join(mel_left))
        right_curve = mel.eval(" ".join(mel_right))

    lofted = cmds.loft(
        right_curve,
        left_curve,
        constructionHistory=False,
        uniform=True,
        close=False,
        autoReverse=False,
        degree=3,
        sectionSpans=1,
        range=False,
        polygon=0,
        reverseSurfaceNormals=False,
        name=config.CYC_NAME,
    )
    cyc_nurbs = _as_transform(lofted)

    for crv in [left_curve, right_curve]:
        if cmds.objExists(crv):
            cmds.delete(crv)

    cyc = _as_transform(
        cmds.nurbsToPoly(
            cyc_nurbs,
            constructionHistory=False,
            format=2,
            polygonType=1,
            uType=3,
            vType=3,
            uNumber=4,
            vNumber=segs_curve + 4,
            name=f"{config.CYC_NAME}_poly",
        )
    )

    if cmds.objExists(cyc_nurbs):
        cmds.delete(cyc_nurbs)

    cmds.polyNormal(cyc, normalMode=0, userNormalMode=0, ch=False)
    cmds.xform(cyc, centerPivots=True)

    _assign_cyc_shader(cyc)
    cyc = _force_parent(cyc, rig)
    return cyc


# ---------------------------------------------------------------------------
# Skydome
# ---------------------------------------------------------------------------

def _create_skydome(rig: str, preset: LightingPreset) -> str:
    name = "TA_assetRender_skydome"
    transform = cmds.shadingNode("aiSkyDomeLight", asLight=True, name=name)
    short = (cmds.ls(transform, shortNames=True) or [transform])[0]
    if short != name:
        transform = cmds.rename(transform, name)

    shapes = cmds.listRelatives(transform, shapes=True, fullPath=False) or []
    if not shapes:
        raise RuntimeError("Skydome shape not found after creation.")
    shape = shapes[0]

    if not _safe_set(f"{shape}.color", preset.sky_color, "double3"):
        _safe_set(f"{shape}.colorR", preset.sky_color[0])
        _safe_set(f"{shape}.colorG", preset.sky_color[1])
        _safe_set(f"{shape}.colorB", preset.sky_color[2])
    _safe_set(f"{shape}.exposure", preset.sky_exposure)
    _safe_set(f"{shape}.aiSamples", config.LIGHT_SAMPLES)

    transform = _force_parent(transform, rig)
    return transform


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_rig(
    bbox: BBox, options: RigOptions, targets: list[str] | None = None,
) -> list[str]:
    """Create rig nodes. Returns log lines."""
    log: list[str] = []
    size = bbox.size
    dist = size * config.DIST_MULT
    area_scale = size * config.AREA_SCALE_MULT
    cx, cy, cz = bbox.center
    preset = options.get_preset()

    rig = cmds.group(empty=True, name=config.RIG_GRP, world=True)
    log.append(f"Created {config.RIG_GRP}")

    if options.cyclorama:
        _create_cyclorama(bbox, size, rig)
        log.append("  + Cyclorama")

    if options.reference_kit:
        _create_reference_kit(bbox, size, rig)
        log.append("  + Reference kit (chrome + gray spheres)")

    if options.camera:
        if options.tri_cam:
            _create_tri_cam(bbox, dist, rig, targets or [])
            log.append(
                f"  + Tri-Cam ({config.CAM_NAME}, "
                f"{config.CAM_SIDE_NAME}, {config.CAM_HIGH_NAME})"
            )
        else:
            _create_camera(bbox, dist, rig)
            log.append(f"  + Camera ({config.CAM_NAME})")

    if options.key_light:
        key_scale = area_scale * 0.8
        _create_area_light(
            "TA_assetRender_key",
            (cx + dist * 0.6, cy + dist * 1.0, cz + dist * 0.4),
            (key_scale, key_scale, 1.0),
            preset.key_exposure,
            (cx, cy, cz),
            rig,
        )
        log.append(f"  + Key light (exposure: {preset.key_exposure})")

    if options.fill_light:
        fill_scale = area_scale * 1.6
        _create_area_light(
            "TA_assetRender_fill",
            (cx - dist * 0.8, cy + dist * 0.2, cz + dist * 0.7),
            (fill_scale, fill_scale, 1.0),
            preset.fill_exposure,
            (cx, cy, cz),
            rig,
        )
        log.append(f"  + Fill light (exposure: {preset.fill_exposure})")

    if options.rim_light:
        rim_scale = area_scale * 0.6
        _create_area_light(
            "TA_assetRender_rim",
            (cx - dist * 0.5, cy + dist * 1.0, cz - dist * 0.3),
            (rim_scale, rim_scale, 1.0),
            preset.rim_exposure,
            (cx, cy, cz),
            rig,
        )
        log.append(f"  + Rim light (exposure: {preset.rim_exposure})")

    if options.uplight:
        uplight_scale = area_scale * 1.5
        light_y = bbox.min_y - size * 0.1
        light_z = bbox.max_z + size * 0.6
        aim_y = cy + size * 0.3
        _create_area_light(
            "TA_assetRender_uplight",
            (cx, light_y, light_z),
            (uplight_scale, uplight_scale * 0.6, 1.0),
            preset.uplight_exposure,
            (cx, aim_y, cz),
            rig,
        )
        log.append(f"  + Uplight (contrapicado, exposure: {preset.uplight_exposure})")

    if options.skydome:
        _create_skydome(rig, preset)
        log.append(f"  + Skydome (exposure: {preset.sky_exposure})")

    if options.camera and cmds.objExists(config.CAM_NAME):
        cmds.lookThru(config.CAM_NAME)

    if options.lighting_preset != "default":
        log.append(f"  Lighting preset: {preset.label}")

    return log
