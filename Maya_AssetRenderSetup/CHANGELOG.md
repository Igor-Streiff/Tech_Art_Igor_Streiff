# Changelog

All notable changes to **Maya Asset Render Setup**.

## [3.0.9] — 2026-06-23

### Changed
- **UI language:** all tool labels, hints, buttons, dialogs, and log messages are
  now English (previously mixed EN/ES).

## [3.0.8] — 2026-06-23

### Changed
- **Rim light** another ~30% closer (`RIM_LIGHT_OFFSET` × 0.7).

## [3.0.7] — 2026-06-23

### Changed
- **Rim light** ~30% closer to the asset (`RIM_LIGHT_OFFSET` × 0.7).

## [3.0.6] — 2026-06-23

### Changed
- **Cyclorama** scaled down (~40% less floor/wall/width) for character-sized assets.
- **Rim light** placed closer behind the subject (`RIM_LIGHT_OFFSET` in `config.py`).

## [3.0.5] — 2026-06-23

### Fixed
- **Create Setup / MtoA crash** (`arnoldTabLayout not found`): create Arnold options
  via `createOptions()` and tolerate renderer UI refresh when Render Settings
  panel is closed.

### Changed
- Light exposure sliders now start at **0 EV** (no negative values in the UI).

## [3.0.4] — 2026-06-23

### Changed
- **Lighting UI:** removed style presets (Default, Hero, etc.). Each light now has
  its own exposure slider (EV). Values persist in Maya `optionVar`s per profile.

## [3.0.3] — 2026-06-23

### Fixed
- **Hero camera framing on rigged assets:** bbox is computed from visible mesh
  shapes under the selection (not the parent group with controls), and the
  principal camera runs `viewFit` like side/high cameras.

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
