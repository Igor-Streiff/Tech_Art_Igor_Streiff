"""
Generic Material Linker entry point.

    import run_linker
    run_linker.run(r"C:/path/to/material_link_map.json")
"""

from __future__ import annotations

import os
import sys


def run(config_path, dry_run=False):
    linker_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.dirname(linker_dir)
    for path in (scripts_dir, linker_dir):
        if path not in sys.path:
            sys.path.insert(0, path)

    from core import run_with_undo

    config_path = os.path.normpath(config_path)
    if not os.path.isfile(config_path):
        raise IOError(f"Config not found: {config_path}")
    return run_with_undo(config_path, dry_run=dry_run)
