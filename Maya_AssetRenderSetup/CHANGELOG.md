# Changelog

All notable changes to **Maya Asset Render Setup**.

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
