"""Launch UI — no hardcoded paths (uses bootstrap discovery)."""

from __future__ import annotations

import asset_render_setup

asset_render_setup.bootstrap.ensure_on_path()
asset_render_setup.show()
