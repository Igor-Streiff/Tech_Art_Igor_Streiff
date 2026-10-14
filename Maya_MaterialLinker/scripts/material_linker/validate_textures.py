"""
Offline validation: scan sourceimages and print expected links (no Maya required).

    python validate_textures.py
"""

from __future__ import annotations

import json
import os
import sys

MAP_SUFFIXES = (
    "BaseColor",
    "Normal",
    "Roughness",
    "Metalness",
    "Height",
    "Emissive",
)


def project_root():
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )


def parse_texture_name(filename, prefix, extensions):
    base, ext = os.path.splitext(filename)
    if ext.lower() not in extensions:
        return None, None
    head = f"{prefix}_M_"
    if not base.startswith(head):
        return None, None
    rest = base[len(head) :]
    for suffix in sorted(MAP_SUFFIXES, key=len, reverse=True):
        tail = f"_{suffix}"
        if rest.endswith(tail):
            return rest[: -len(tail)], suffix
    return None, None


def main():
    root = project_root()
    config_path = os.path.join(root, "material_link_map.json")
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    prefix = config["texture_prefix"]
    subdir = config.get("sourceimages_subdir", "sourceimages")
    extensions = tuple(ext.lower() for ext in config["texture_extensions"])
    src = os.path.join(root, subdir)

    catalog = {}
    for entry in sorted(os.listdir(src)):
        token, map_suffix = parse_texture_name(entry, prefix, extensions)
        if token:
            catalog.setdefault(token, {})[map_suffix] = entry

    print("=== Material Linker — offline texture scan ===")
    print(f"Project: {root}")
    print(f"Found {sum(len(m) for m in catalog.values())} maps across {len(catalog)} tokens\n")

    for item in config["mappings"]:
        mat = item["maya_material"]
        token = item["texture_token"]
        maps = catalog.get(token, {})
        print(f"{mat}  ->  token '{token}'  ({len(maps)}/6 core maps)")
        for suffix in MAP_SUFFIXES:
            status = maps.get(suffix, "MISSING")
            mark = "OK" if status != "MISSING" else "!!"
            print(f"    [{mark}] {suffix}: {status}")
        print()

    return 0 if all(catalog.get(m["texture_token"]) for m in config["mappings"]) else 1


if __name__ == "__main__":
    sys.exit(main())
