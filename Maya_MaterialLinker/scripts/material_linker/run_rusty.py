"""
Run Material Linker for the Rusty Arnold project (one-click).

Usage in Maya Script Editor (Python):

    import run_rusty
    run_rusty.link_all()

Or with dry-run (report only, no node changes):

    run_rusty.link_all(dry_run=True)
"""

from __future__ import annotations

import os
import sys


def _project_root():
    # scripts/material_linker/run_rusty.py -> project root is two levels up from scripts/
    here = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.dirname(here)
    return os.path.dirname(scripts_dir)


def _ensure_paths():
    root = _project_root()
    scripts = os.path.join(root, "scripts")
    linker = os.path.join(scripts, "material_linker")
    for path in (scripts, linker):
        if path not in sys.path:
            sys.path.insert(0, path)
    return root


def link_all(dry_run=False):
    root = _ensure_paths()
    config_path = os.path.join(root, "material_link_map.json")
    if not os.path.isfile(config_path):
        raise IOError(f"Config not found: {config_path}")

    from core import run_with_undo

    print(f"Material Linker — project: {root}")
    print(f"Config: {config_path}")
    print(f"Dry run: {dry_run}\n")
    return run_with_undo(config_path, dry_run=dry_run)


if __name__ == "__main__":
    link_all()
