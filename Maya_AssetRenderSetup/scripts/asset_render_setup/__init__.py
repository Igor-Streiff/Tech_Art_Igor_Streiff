"""Maya Asset Render Setup — Arnold preview rig + fast render."""

from .config import __version__
from .bootstrap import (
    ensure_on_path,
    iter_scripts_candidates,
    register_scripts_dir,
    resolve_scripts_dir,
    tool_root,
)
from .config import LIGHTING_PRESETS, LightingPreset, RigOptions
from .core import create_setup
from .render import fast_render
from .ui import show

__all__ = [
    "__version__",
    "LightingPreset",
    "LIGHTING_PRESETS",
    "RigOptions",
    "create_setup",
    "fast_render",
    "show",
    "ensure_on_path",
    "register_scripts_dir",
    "resolve_scripts_dir",
    "iter_scripts_candidates",
    "tool_root",
]
