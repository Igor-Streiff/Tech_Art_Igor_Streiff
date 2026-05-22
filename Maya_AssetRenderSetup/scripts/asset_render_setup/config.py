"""Defaults for Maya Asset Render Setup."""

from __future__ import annotations

from dataclasses import dataclass

__version__ = "3.0.1"

RIG_GRP = "TA_AssetRender_RIG"
RIG_PREFIX = "TA_assetRender_"
CAM_NAME = "TA_assetRender_cam"
CYC_NAME = "TA_assetRender_cyc"

# Tri-cam
CAM_SIDE_NAME = "TA_assetRender_cam_side"
CAM_HIGH_NAME = "TA_assetRender_cam_high"
TRI_CAM_NAMES = (CAM_NAME, CAM_SIDE_NAME, CAM_HIGH_NAME)

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

# 3-point lighting defaults (also the "default" preset values)
KEY_EXPOSURE = 4.0
FILL_EXPOSURE = 4.0
RIM_EXPOSURE = 9.0
UPLIGHT_EXPOSURE = 4.0
SKY_EXPOSURE = 0.5
SKY_COLOR = (0.9, 0.92, 0.95)

CAM_FOCAL_LENGTH = 50.0
DIST_MULT = 2.8
AREA_SCALE_MULT = 1.2

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
    "default": LightingPreset(
        "Default", KEY_EXPOSURE, FILL_EXPOSURE, RIM_EXPOSURE,
        UPLIGHT_EXPOSURE, SKY_EXPOSURE, SKY_COLOR,
    ),
    "product": LightingPreset(
        "Product", 5.0, 5.5, 6.0, 3.0, 1.0, (1.0, 1.0, 1.0),
    ),
    "hero": LightingPreset(
        "Hero", 5.5, 2.5, 10.0, 5.0, 0.3, (0.85, 0.88, 0.95),
    ),
    "soft_fill": LightingPreset(
        "Soft Fill", 4.5, 5.0, 5.0, 3.0, 1.2, (0.95, 0.93, 0.9),
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
    tri_cam: bool = False
    reference_kit: bool = False
    lighting_preset: str = "default"
    # Fast Render: when True, temporarily disable scene AOVs and keep only beauty PNGs.
    beauty_only: bool = False

    @classmethod
    def all_enabled(cls) -> RigOptions:
        return cls()

    def get_preset(self) -> LightingPreset:
        return LIGHTING_PRESETS.get(self.lighting_preset, LIGHTING_PRESETS["default"])


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
