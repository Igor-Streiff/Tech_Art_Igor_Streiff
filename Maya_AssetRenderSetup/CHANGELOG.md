# Changelog

All notable changes to **Maya Asset Render Setup**.

## [3.0.2] — 2026-06-12

### Added
- **Orthographic isometric cameras** (left / right): game-style 45°/30° iso views
  with parallel projection and deterministic, aspect-aware framing.
- **Selectable cameras**: enable any combination of hero, side, high, and iso
  cameras individually; Fast Render renders every rig camera present in the scene.
- **Clay render**: temporary matte-clay material override during Fast Render, plus
  Apply / Restore buttons for interactive RenderView preview. Original shaders are
  always restored.
- **Blockout** lighting style for untextured models (minimal skydome, strong key).

### Fixed
- Area lights now keep consistent brightness at any asset scale. `aiNormalize=ON`
  (the previous default) held total power constant, so irradiance fell as `1/dist²`
  when the rig expanded for larger assets. `aiNormalize=OFF` makes intensity
  represent luminance; since light area and distance both scale with `bbox.size`,
  irradiance stays constant regardless of asset size.
- Cameras now keep their aim. The aim constraint is baked to a static rotation
  before the helper locator is deleted (previously the orientation was lost).

### Changed
- Recalibrated all lighting styles for `normalize=OFF` with a ~4:1 key/fill ratio
  so combined lights no longer overexpose.
- Reorganized the UI into **Rig**, **Lights**, and **Fast Render** sections; the
  lighting preset menu now shows readable style names.

## [3.0.1] — 2026-05-21

### Fixed
- Fast Render no longer auto-builds the rig when setup is missing (shows dialog instead).
- Correct beauty vs AOV file identification when scene AOVs are enabled.
- Install/uninstall work from Maya Script Editor (`__file__` fallback, `saveAllShelves` API).
- Single render per camera (removed silent double-render fallback).

### Changed
- Output naming: `{scene}_beauty.png`, `{scene}_{aov}.png` (tri-cam: `{scene}_main_beauty.png`, etc.).
- Optional **Beauty only** UI toggle (respects scene AOVs when off).
- Removed redundant `ta_shelf_launch.py` and legacy `install/shelf_utils.py`.

## [3.0.0] — 2026-05

### Added
- Tri-Cam mode (main / side / high) with contact-sheet Fast Render.
- Reference kit (chrome + 18% gray spheres).
- Lighting presets: Default, Product, Hero, Soft Fill.
- Self-contained install/uninstall scripts.

## [2.0.0]

### Added
- Toggle UI, Create Setup, Fast Render, Arnold preview rig (single camera, cyclorama, 3-point + skydome).
