"""Defaults for Maya Asset Render Setup."""

from __future__ import annotations

from dataclasses import dataclass

__version__ = "3.0.2"

RIG_GRP = "TA_AssetRender_RIG"
RIG_PREFIX = "TA_assetRender_"
CAM_NAME = "TA_assetRender_cam"
CYC_NAME = "TA_assetRender_cyc"

# Tri-cam (legacy bundle: main + side + high)
CAM_SIDE_NAME = "TA_assetRender_cam_side"
CAM_HIGH_NAME = "TA_assetRender_cam_high"
TRI_CAM_NAMES = (CAM_NAME, CAM_SIDE_NAME, CAM_HIGH_NAME)

# Isometric cameras (elevated diagonal, game-style 3/4)
CAM_ISO_LEFT_NAME = "TA_assetRender_cam_isoLeft"
CAM_ISO_RIGHT_NAME = "TA_assetRender_cam_isoRight"

# All possible rig cameras in render order (name, output suffix)
ALL_CAM_SPECS: tuple[tuple[str, str], ...] = (
    (CAM_NAME,          "main"),
    (CAM_SIDE_NAME,     "side"),
    (CAM_HIGH_NAME,     "high"),
    (CAM_ISO_LEFT_NAME, "isoLeft"),
    (CAM_ISO_RIGHT_NAME,"isoRight"),
)

# Reference kit (chrome mirror ball + 18% gray ball)
REF_CHROME_NAME = "TA_assetRender_refChrome"
REF_GRAY_NAME = "TA_assetRender_refGray"
REF_SPHERE_SEGS = 24
REF_SPHERE_SCALE_MULT = 0.25
REF_GAP_MULT = 0.5
REF_CHROME_COLOR = (0.95, 0.95, 0.95)
REF_GRAY_VALUE = 0.18

OPTIONVAR_OUTPUT_DIR = "TA_assetRenderSetup_outputDir"

# Fast Render file naming
RENDER_USE_TIMESTAMP = False  # True → Asset_scene_20260521_213812.png
PNG_INCOMPATIBLE_AOVS = frozenset({"N", "Z"})  # vector/float AOVs — skip in sidecar labels

# Default beauty preset (1920x1080, no DOF)
RES_WIDTH = 1920
RES_HEIGHT = 1080
RES_ASPECT = 1.777

AA_SAMPLES = 7
DIFFUSE_SAMPLES = 3
SPECULAR_SAMPLES = 2
TRANSMISSION_SAMPLES = 6
SSS_SAMPLES = 4
LIGHT_SAMPLES = 3

# 3-point lighting defaults — calibrated for aiAreaLight normalize=OFF.
# Key:Fill ratio ~4:1 (2 EV stops) so they don't overexpose when combined.
# Fill is a shadow-opener, not a co-illuminator.
KEY_EXPOSURE = 3.5     # dominant light — correct alone, anchor of the setup
FILL_EXPOSURE = 1.5    # 2 EV below key → 4:1 ratio, proper shadow fill
RIM_EXPOSURE = 4.5     # edge accent — focused on back silhouette
UPLIGHT_EXPOSURE = 2.0
SKY_EXPOSURE = 0.2     # stable ambient base
SKY_COLOR = (0.9, 0.92, 0.95)

CAM_FOCAL_LENGTH = 50.0
DIST_MULT = 2.8
AREA_SCALE_MULT = 1.2

# Iso cameras: orthographic width as a fraction of bbox.size. The iso 45°/30°
# projection of a cube spans ~1.4× its max axis; 1.8 leaves margin before
# viewFit refines the framing to the actual geometry.
ISO_ORTHO_WIDTH_MULT = 1.8

# Clay override material (Fast Render clay / RenderView preview).
# Dark warm gray (~0.22): with all lights combined a 0.45 albedo still washed
# to near-white because the contributions accumulate. A darker base keeps tonal
# range available so the key→fill→shadow gradient stays visible when fully lit.
CLAY_COLOR = (0.22, 0.21, 0.19)
CLAY_SPECULAR = 0.05
CLAY_ROUGHNESS = 0.95

# Infinity cove multipliers (fraction of bbox size)
CYC_WIDTH_MULT = 20.0
CYC_FLOOR_DEPTH_MULT = 12.0
CYC_CURVE_RADIUS_MULT = 2.5
CYC_WALL_HEIGHT_MULT = 12.0
CYC_WALL_BACK_PAD_MULT = 2.5
CYC_SEGS_CURVE = 32
CYC_SEGS_WIDTH = 4
CYC_COLOR = (0.75, 0.75, 0.75)
# Floor Y offset: positive = floor moves UP (asset slightly buried),
# negative = floor moves DOWN (asset floats more). Use this to fix
# assets that float because their bbox extends below the visible geometry
# (e.g. parent group with offset, hidden support nodes).
CYC_FLOOR_Y_OFFSET_MULT = 0.0


# ---------------------------------------------------------------------------
# Lighting presets
# ---------------------------------------------------------------------------

@dataclass
class LightingPreset:
    label: str
    key_exposure: float
    fill_exposure: float
    rim_exposure: float
    uplight_exposure: float
    sky_exposure: float
    sky_color: tuple[float, float, float]


LIGHTING_PRESETS: dict[str, LightingPreset] = {
    # Balanced studio — key correct alone, fill opens shadows, rim as accent.
    "default": LightingPreset(
        "Default", KEY_EXPOSURE, FILL_EXPOSURE, RIM_EXPOSURE,
        UPLIGHT_EXPOSURE, SKY_EXPOSURE, SKY_COLOR,
    ),
    # Clean product — bright key, minimal fill (4:1 ratio), subtle rim, white sky.
    "product": LightingPreset(
        "Product", 4.0, 2.0, 4.5, 1.5, 0.5, (1.0, 1.0, 1.0),
    ),
    # Dramatic — strong key, deep fill (8:1 ratio), punchy rim, near-zero sky.
    "hero": LightingPreset(
        "Hero", 4.5, 1.0, 6.5, 2.0, -0.5, (0.85, 0.88, 0.95),
    ),
    # Soft — balanced key/fill (2:1 ratio), soft rim, higher sky for diffuse look.
    "soft_fill": LightingPreset(
        "Soft Fill", 3.0, 2.0, 3.5, 1.5, 0.8, (0.95, 0.93, 0.9),
    ),
    # Blockout — strong directional key, minimal fill, skydome off. Reads form.
    "clay": LightingPreset(
        "Blockout", 3.5, 0.5, 5.0, 1.0, -1.0, (0.88, 0.90, 0.95),
    ),
}


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------

@dataclass
class RigOptions:
    camera: bool = True
    cyclorama: bool = True
    key_light: bool = True
    fill_light: bool = True
    rim_light: bool = True
    uplight: bool = False
    skydome: bool = True
    arnold_settings: bool = True
    # Individual camera flags (tri_cam kept for backward compat: sets side+high)
    tri_cam: bool = False
    cam_side: bool = False
    cam_high: bool = False
    cam_iso_left: bool = False
    cam_iso_right: bool = False
    reference_kit: bool = False
    lighting_preset: str = "default"
    # Fast Render: when True, temporarily disable scene AOVs and keep only beauty PNGs.
    beauty_only: bool = False
    # Fast Render: when True, temporarily override all asset materials with a clay shader.
    clay_render: bool = False

    @classmethod
    def all_enabled(cls) -> RigOptions:
        return cls()

    def get_preset(self) -> LightingPreset:
        return LIGHTING_PRESETS.get(self.lighting_preset, LIGHTING_PRESETS["default"])

    def wants_side_cam(self) -> bool:
        return self.cam_side or self.tri_cam

    def wants_high_cam(self) -> bool:
        return self.cam_high or self.tri_cam


@dataclass
class BBox:
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @property
    def center(self) -> tuple[float, float, float]:
        return (
            (self.min_x + self.max_x) * 0.5,
            (self.min_y + self.max_y) * 0.5,
            (self.min_z + self.max_z) * 0.5,
        )

    @property
    def size(self) -> float:
        dx = self.max_x - self.min_x
        dy = self.max_y - self.min_y
        dz = self.max_z - self.min_z
        return max(dx, dy, dz, 0.001)
