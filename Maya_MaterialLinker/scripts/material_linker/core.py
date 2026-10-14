"""
Material Linker — Substance TIFF textures -> Arnold aiStandardSurface (Maya).

Convention: {texture_prefix}_M_{texture_token}_{MapSuffix}.ext
Auto material: M_{texture_token}  |  Custom aliases via material_link_map.json
"""

from __future__ import annotations

import json
import os
import re

try:
    import maya.cmds as cmds
    import maya.utils as maya_utils
except ImportError:
    cmds = None
    maya_utils = None

MAP_SUFFIXES = (
    "BaseColor",
    "Normal",
    "Roughness",
    "Metalness",
    "Height",
    "Emissive",
    "Opacity",
    "AO",
)

MAP_BINDINGS = {
    "BaseColor": {
        "attribute": "baseColor",
        "attr_aliases": ("base_color", "baseColor"),
        "kind": "color",
        "color_space": "sRGB",
    },
    "Roughness": {
        "attribute": "specularRoughness",
        "attr_aliases": ("specular_roughness", "diffuse_roughness", "specularRoughness"),
        "kind": "float",
        "color_space": "Raw",
    },
    "Metalness": {
        "attribute": "metalness",
        "attr_aliases": ("metalness",),
        "kind": "float",
        "color_space": "Raw",
    },
    "Normal": {
        "attribute": "normalCamera",
        "attr_aliases": ("normal_camera", "normalCamera"),
        "kind": "normal",
        "middle": "aiNormalMap",
        "color_space": "Raw",
    },
    "Emissive": {
        "attribute": "emissionColor",
        "attr_aliases": ("emission_color", "emissionColor"),
        "kind": "color",
        "color_space": "sRGB",
        "also_set": {"emission": 1.0},
        "optional": True,
    },
    "Height": {
        "attribute": "bump",
        "attr_aliases": ("bump", "bump_map"),
        "kind": "bump",
        "middle": "aiBump2d",
        "color_space": "Raw",
        "optional": True,
    },
}


def _require_maya():
    if cmds is None:
        raise RuntimeError("Material Linker must run inside Maya (maya.cmds not available).")


def _safe_name(text):
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


def _node_attr(node, attr_candidates):
    for attr in attr_candidates:
        short = attr.split(".")[-1]
        if cmds.attributeQuery(short, node=node, exists=True):
            return f"{node}.{short}"
    return None


def _first_attr_plug(node, attr_names):
    """Return node.attr for the first attribute that exists on node."""
    for name in attr_names:
        if cmds.attributeQuery(name, node=node, exists=True):
            return f"{node}.{name}"
    return None


class MaterialLinker:
    def __init__(self, config_path=None, config_dict=None, dry_run=False):
        _require_maya()
        self.dry_run = dry_run
        self.config = config_dict or self._load_config(config_path)
        self.texture_prefix = self.config.get("texture_prefix", "")
        self.extensions = tuple(
            self.config.get("texture_extensions", [".tif", ".tiff", ".png", ".exr"])
        )
        self.source_dir = self._resolve_sourceimages_dir()
        self.textures = self._scan_textures()
        self.skip_maps = set(self.config.get("skip_maps") or [])
        self.report = {
            "linked": [],
            "skipped_existing": [],
            "missing_maps": [],
            "missing_materials": [],
            "errors": [],
            "warnings": [],
        }

    @staticmethod
    def _load_config(config_path):
        with open(config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _resolve_sourceimages_dir(self):
        subdir = self.config.get("sourceimages_subdir", "sourceimages")
        try:
            resolved = cmds.workspace(fileRuleEntry="sourceImages", expandName=True)
            if resolved and os.path.isdir(resolved):
                return os.path.normpath(resolved)
        except Exception:
            pass

        project_root = cmds.workspace(q=True, rootDirectory=True)
        if not project_root:
            raise RuntimeError("Set a Maya project (File > Project Window) before running Material Linker.")
        path = os.path.join(project_root, subdir)
        if not os.path.isdir(path):
            raise RuntimeError(f"sourceimages folder not found: {path}")
        return os.path.normpath(path)

    def _parse_texture_name(self, filename):
        base, ext = os.path.splitext(filename)
        if ext.lower() not in self.extensions:
            return None, None

        prefix = self.texture_prefix
        marker = "_M_"
        if prefix:
            head = f"{prefix}{marker}"
            if not base.startswith(head):
                return None, None
            rest = base[len(head) :]
        elif marker in base:
            rest = base.split(marker, 1)[1]
        else:
            return None, None

        for suffix in sorted(MAP_SUFFIXES, key=len, reverse=True):
            tail = f"_{suffix}"
            if rest.endswith(tail):
                token = rest[: -len(tail)]
                if token:
                    return token, suffix
        return None, None

    def _scan_textures(self):
        catalog = {}
        if not os.path.isdir(self.source_dir):
            self.report["errors"].append(f"Cannot read directory: {self.source_dir}")
            return catalog

        for entry in os.listdir(self.source_dir):
            token, map_suffix = self._parse_texture_name(entry)
            if not token:
                continue
            catalog.setdefault(token, {})[map_suffix] = os.path.join(self.source_dir, entry)
        return catalog

    def _collect_mappings(self):
        explicit = self.config.get("mappings") or []
        pairs = []

        for item in explicit:
            maya_mat = item.get("maya_material")
            token = item.get("texture_token")
            if maya_mat and token:
                pairs.append((maya_mat, token))

        if pairs:
            return pairs

        auto = []
        for shader in cmds.ls(type="aiStandardSurface") or []:
            short = shader.split("|")[-1]
            if short.startswith("M_"):
                token = short[2:]
                if token in self.textures:
                    auto.append((short, token))
        return auto

    def _find_shader(self, name):
        if cmds.objExists(name):
            node_type = cmds.nodeType(name)
            if node_type == "aiStandardSurface":
                return name
            shapes = cmds.listConnections(name, s=False, d=True, type="aiStandardSurface") or []
            if shapes:
                return shapes[0]
        matches = cmds.ls(name, type="aiStandardSurface") or []
        return matches[0] if matches else None

    def _file_path_on_node(self, file_node):
        if not file_node or not cmds.objExists(file_node):
            return None
        try:
            return os.path.normpath(
                cmds.getAttr(f"{file_node}.fileTextureName").replace("\\", "/")
            )
        except Exception:
            return None

    def _find_file_for_target(self, shader, target_plug):
        sources = cmds.listConnections(target_plug, s=True, d=False, plugs=True) or []
        visited = set()
        for plug in sources:
            node = plug.split(".")[0]
            if node in visited:
                continue
            visited.add(node)
            node_type = cmds.nodeType(node)
            if node_type == "file":
                return node
            upstream = cmds.listConnections(node, s=True, d=False) or []
            for up in upstream:
                if cmds.nodeType(up) == "file":
                    return up
        return None

    def _set_file_path(self, file_node, path):
        norm = os.path.normpath(path).replace("\\", "/")
        if self.dry_run:
            return
        cmds.setAttr(f"{file_node}.fileTextureName", norm, type="string")

    def _set_color_space(self, file_node, color_space):
        if self.dry_run:
            return
        for attr in ("colorSpace", "cs"):
            if cmds.attributeQuery(attr, node=file_node, exists=True):
                try:
                    cmds.setAttr(f"{file_node}.{attr}", color_space, type="string")
                except Exception:
                    pass
                break

    def _connect(self, source_plug, dest_plug, force=False):
        if self.dry_run:
            return
        if not cmds.objExists(source_plug.split(".")[0]):
            raise ValueError(f"Source node does not exist: {source_plug}")
        dest_attr = dest_plug.split(".")[-1]
        dest_node = dest_plug.split(".")[0]
        if not cmds.objExists(dest_node):
            raise ValueError(f"Destination node does not exist: {dest_plug}")
        if not cmds.attributeQuery(dest_attr, node=dest_node, exists=True):
            raise ValueError(f"Destination attribute does not exist: {dest_plug}")
        cmds.connectAttr(source_plug, dest_plug, force=force)

    def _create_file_node(self, shader, map_suffix):
        safe_shader = _safe_name(shader.split("|")[-1])
        safe_map = _safe_name(map_suffix)
        name = f"{safe_shader}_file_{safe_map}"
        if self.dry_run:
            return name
        return cmds.shadingNode("file", asTexture=True, name=name)

    def _create_middle_node(self, binding, shader, map_suffix):
        node_type = binding["middle"]
        safe_shader = _safe_name(shader.split("|")[-1])
        safe_map = _safe_name(map_suffix)
        name = f"{safe_shader}_{node_type}_{safe_map}"
        if self.dry_run:
            return name
        node = cmds.shadingNode(node_type, asShader=True, name=name)
        if not cmds.objExists(node):
            raise RuntimeError(f"Failed to create {node_type} node: {name}")
        return node

    def _connect_file_to_dest(self, file_node, dest_plug, kind, binding, shader, map_suffix):
        """file -> shader (direct). Avoids aiImage.input (not present in all MtoA builds)."""
        if kind == "color":
            self._connect(f"{file_node}.outColor", dest_plug, force=True)
            return

        if kind == "float":
            self._connect(f"{file_node}.outColorR", dest_plug, force=True)
            return

        if kind == "normal":
            middle = self._create_middle_node(binding, shader, map_suffix)
            src_plug = f"{file_node}.outColor"
            in_plug = _first_attr_plug(middle, ("input", "input1", "map", "bumpValue"))
            if not in_plug:
                raise ValueError(
                    f"No supported input on {middle} "
                    f"(tried input, input1, map, bumpValue)."
                )
            if not cmds.isConnected(src_plug, in_plug):
                self._connect(src_plug, in_plug, force=True)
            out_plug = _first_attr_plug(middle, ("outValue", "outNormal", "output"))
            if not out_plug:
                raise ValueError(f"No output on {middle} (tried outValue, outNormal, output).")
            self._connect(out_plug, dest_plug, force=True)
            return

        if kind == "bump":
            middle = self._create_middle_node(binding, shader, map_suffix)
            bump_in = _first_attr_plug(middle, ("bumpValue", "input", "input1"))
            if not bump_in:
                raise ValueError(f"No bump input on {middle}.")
            self._connect(f"{file_node}.outColorR", bump_in, force=True)
            bump_out = _first_attr_plug(middle, ("outValue", "outNormal", "output"))
            if bump_out:
                self._connect(bump_out, dest_plug, force=True)

    def _wire_texture(self, shader, map_suffix, file_path, binding):
        dest_plug = _node_attr(shader, binding["attr_aliases"])
        if not dest_plug:
            if binding.get("optional"):
                self.report["warnings"].append(
                    f"{shader}: attribute for {map_suffix} not found — skipped."
                )
                return "skip"
            self.report["errors"].append(
                f"{shader}: no attribute for map {map_suffix} ({binding['attr_aliases']})."
            )
            return "error"

        norm_path = os.path.normpath(file_path)
        existing_file = self._find_file_for_target(shader, dest_plug)
        if existing_file:
            current = self._file_path_on_node(existing_file)
            if current and os.path.normpath(current) == norm_path:
                self.report["skipped_existing"].append(
                    f"{shader}.{map_suffix} already linked -> {os.path.basename(file_path)}"
                )
                return "skip"
            file_node = existing_file
        else:
            file_node = self._create_file_node(shader, map_suffix)

        self._set_file_path(file_node, norm_path)
        self._set_color_space(file_node, binding["color_space"])

        kind = binding["kind"]
        if not self.dry_run:
            try:
                self._connect_file_to_dest(
                    file_node, dest_plug, kind, binding, shader, map_suffix
                )
            except Exception as exc:
                self.report["errors"].append(f"{shader}.{map_suffix}: {exc}")
                return "error"

        also = binding.get("also_set") or {}
        for attr, value in also.items():
            plug = _node_attr(shader, (attr,))
            if plug and not self.dry_run:
                cmds.setAttr(plug, value)

        return "linked"

    def link_material(self, maya_material, texture_token):
        shader = self._find_shader(maya_material)
        if not shader:
            self.report["missing_materials"].append(maya_material)
            return

        maps = self.textures.get(texture_token, {})
        if not maps:
            self.report["errors"].append(f"No textures found for token: {texture_token}")
            return

        for map_suffix, binding in MAP_BINDINGS.items():
            if map_suffix in self.skip_maps:
                self.report["warnings"].append(
                    f"{maya_material}: skipped {map_suffix} (listed in skip_maps)."
                )
                continue

            path = maps.get(map_suffix)
            if not path:
                if not binding.get("optional"):
                    self.report["missing_maps"].append(
                        f"{maya_material} ({texture_token}): missing {map_suffix}"
                    )
                continue

            result = self._wire_texture(shader, map_suffix, path, binding)
            if result == "linked":
                self.report["linked"].append(
                    f"{shader} <- {map_suffix} ({os.path.basename(path)})"
                )

    def run(self):
        mappings = self._collect_mappings()
        if not mappings:
            self.report["warnings"].append(
                "No mappings defined and no auto-match materials found (M_{token})."
            )
            return self.report

        for maya_material, texture_token in mappings:
            self.link_material(maya_material, texture_token)

        return self.report

    def print_report(self):
        lines = ["", "=== Material Linker Report ===", f"Textures dir: {self.source_dir}"]
        sections = (
            ("LINKED", "linked"),
            ("SKIPPED (already correct)", "skipped_existing"),
            ("MISSING MAPS", "missing_maps"),
            ("MISSING MATERIALS", "missing_materials"),
            ("WARNINGS", "warnings"),
            ("ERRORS", "errors"),
        )
        for title, key in sections:
            items = self.report.get(key) or []
            if items:
                lines.append(f"\n{title}:")
                for item in items:
                    lines.append(f"  - {item}")
        if len(lines) == 3:
            lines.append("\nNothing to report.")
        text = "\n".join(lines)
        print(text)
        return text


def run_from_config(config_path, dry_run=False):
    linker = MaterialLinker(config_path=config_path, dry_run=dry_run)
    linker.run()
    linker.print_report()
    return linker.report


def run_with_undo(config_path, dry_run=False):
    """Run linker wrapped in a Maya undo chunk."""

    def _inner():
        _require_maya()
        cmds.undoInfo(openChunk=True)
        try:
            return run_from_config(config_path, dry_run=dry_run)
        finally:
            cmds.undoInfo(closeChunk=True)

    if maya_utils:
        return maya_utils.executeInMainThreadWithResult(_inner)
    return _inner()
