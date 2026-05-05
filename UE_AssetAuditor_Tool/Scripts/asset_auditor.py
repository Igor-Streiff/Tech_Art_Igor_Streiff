import unreal
import json
import os
import re
import datetime


class UEAssetAuditorDB:
    """
    Technical Asset Auditor for Unreal Engine 5.
    Generates a versioned JSON report AND an interactive HTML dashboard.
    """

    def __init__(self):
        self.asset_reg = unreal.AssetRegistryHelpers.get_asset_registry()
        self.scene_name = self._get_scene_name()
        self.reports_dir = self._get_reports_dir()
        self.version = self._next_version()

        self.report = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scene": self.scene_name,
            "version": self.version,
            "author": "Igor G. Streiff",
            "summary": {
                "meshes": 0,
                "textures": 0,
                "materials": 0,
                "lights": 0,
                "audio": 0,
                "blueprints": 0,
                "sequencers": 0,
                "warnings": 0
            },
            "meshes": [],
            "textures": [],
            "materials": [],
            "lights": [],
            "environment": [],
            "audio": [],
            "blueprints": [],
            "sequencers": [],
            "warnings": []
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_scene_name(self):
        """Gets the project name from the .uproject file."""
        try:
            name = unreal.SystemLibrary.get_game_name()
            if name:
                return re.sub(r'[\\/*?:"<>|]', '_', name)
        except Exception:
            pass
        return "UnknownProject"

    def _get_reports_dir(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tool_dir = os.path.dirname(script_dir)
        reports = os.path.join(tool_dir, "Reports")
        os.makedirs(reports, exist_ok=True)
        return reports

    def _next_version(self):
        v = 0
        while True:
            tag = "v{:02d}".format(v)
            path = os.path.join(self.reports_dir, "Audit_{}_{}.json".format(self.scene_name, tag))
            if not os.path.exists(path):
                return tag
            v += 1

    def _get_assets_by_type(self, class_name):
        """Use ARFilter with TopLevelAssetPath (UE5 compatible). Only scans /Game/."""
        ar_filter = unreal.ARFilter(
            class_paths=[unreal.TopLevelAssetPath("/Script/Engine", class_name)],
            package_paths=["/Game"],
            recursive_paths=True,
            recursive_classes=True
        )
        return self.asset_reg.get_assets(ar_filter)

    def _warn(self, tag, message, priority="Medium"):
        self.report["warnings"].append({
            "tag": tag,
            "msg": message,
            "priority": priority
        })
        self.report["summary"]["warnings"] += 1

    # ------------------------------------------------------------------
    # Audit modules
    # ------------------------------------------------------------------

    def audit_meshes(self, high_poly_threshold=100000):
        unreal.log("Auditor: Scanning meshes...")
        assets = self._get_assets_by_type("StaticMesh")
        total = len(assets)
        self.report["summary"]["meshes"] = total
        if total == 0:
            return

        with unreal.ScopedSlowTask(total, "Auditing Meshes...") as task:
            task.make_dialog(True)
            for ad in assets:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    mesh = ad.get_asset()
                    if mesh is None:
                        continue
                    num_lods = mesh.get_num_lods()
                    nanite_cfg = mesh.get_editor_property("nanite_settings")
                    nanite_on = nanite_cfg.enabled if nanite_cfg else False
                    mat_slots = len(mesh.static_materials)
                    name = str(ad.asset_name)

                    # Collision check
                    complex_as_simple = False
                    try:
                        body_setup = mesh.get_editor_property("body_setup")
                        if body_setup:
                            c_flag = body_setup.get_editor_property("collision_trace_flag")
                            if str(c_flag) == "CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE":
                                complex_as_simple = True
                    except Exception:
                        pass

                    # Geometry data from LOD 0 (base mesh)
                    vertices = 0
                    triangles = 0
                    has_ngon_risk = False
                    try:
                        vertices = mesh.get_num_vertices(0)
                        triangles = mesh.get_num_triangles(0)
                        # Heuristic: in a clean quad mesh, tris ~ verts * 2.
                        # If tris/verts ratio is unusually high, source likely had ngons.
                        if vertices > 0 and triangles > 0:
                            ratio = triangles / vertices
                            if ratio > 3.0:
                                has_ngon_risk = True
                    except Exception:
                        pass

                    # Warnings
                    if not nanite_on and num_lods < 3:
                        self._warn("MESH_LOD", "'{}' has no Nanite and less than 3 LODs.".format(name), "High")
                    if mat_slots > 5:
                        self._warn("MESH_SLOTS", "'{}' has {} material slots. Consider merging.".format(name, mat_slots), "Medium")
                    if triangles > high_poly_threshold:
                        self._warn("MESH_HEAVY", "'{}' has {:,} triangles. Consider optimization.".format(name, triangles), "High")
                    if has_ngon_risk:
                        self._warn("MESH_NGON", "'{}' has suspicious topology (possible ngons in source).".format(name), "Low")
                    if complex_as_simple:
                        self._warn("MESH_COLLISION", "'{}' uses Complex Collision as Simple (high CPU cost).".format(name), "High")

                    self.report["meshes"].append({
                        "name": name,
                        "vertices": vertices,
                        "triangles": triangles,
                        "lods": num_lods,
                        "nanite": nanite_on,
                        "ngon_risk": has_ngon_risk,
                        "complex_collision": complex_as_simple,
                        "material_slots": mat_slots,
                        "path": str(ad.package_name)
                    })
                except Exception as exc:
                    unreal.log_warning("Auditor: mesh error on {}: {}".format(ad.asset_name, exc))

    def audit_textures(self, max_res=2048):
        unreal.log("Auditor: Scanning textures...")
        assets = self._get_assets_by_type("Texture2D")
        total = len(assets)
        self.report["summary"]["textures"] = total
        if total == 0:
            return

        with unreal.ScopedSlowTask(total, "Auditing Textures...") as task:
            task.make_dialog(True)
            for ad in assets:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    tex = ad.get_asset()
                    if tex is None:
                        continue
                    w = tex.blueprint_get_size_x()
                    h = tex.blueprint_get_size_y()
                    name = str(ad.asset_name)

                    if w > max_res or h > max_res:
                        self._warn("TEX_LARGE", "'{}' is {}x{}.".format(name, w, h), "Medium")

                    self.report["textures"].append({
                        "name": name,
                        "width": w,
                        "height": h,
                        "path": str(ad.package_name)
                    })
                except Exception as exc:
                    unreal.log_warning("Auditor: texture error on {}: {}".format(ad.asset_name, exc))

    def audit_materials(self):
        unreal.log("Auditor: Scanning materials...")
        assets = self._get_assets_by_type("Material")
        total = len(assets)
        self.report["summary"]["materials"] = total
        if total == 0:
            return

        with unreal.ScopedSlowTask(total, "Auditing Materials...") as task:
            task.make_dialog(True)
            for ad in assets:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    mat = ad.get_asset()
                    if mat is None:
                        continue
                    name = str(ad.asset_name)
                    blend = mat.get_editor_property("blend_mode")

                    if blend == unreal.BlendMode.BLEND_TRANSLUCENT:
                        self._warn("MAT_TRANSLUCENT", "'{}' uses translucency (high GPU cost).".format(name), "Medium")

                    self.report["materials"].append({
                        "name": name,
                        "blend_mode": str(blend),
                        "path": str(ad.package_name)
                    })
                except Exception:
                    continue

    def audit_lights(self):
        unreal.log("Auditor: Scanning lights...")
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        count = 0

        with unreal.ScopedSlowTask(len(actors), "Auditing Lights...") as task:
            task.make_dialog(True)
            for actor in actors:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, actor.get_name())
                try:
                    if isinstance(actor, unreal.Light):
                        count += 1
                        self.report["lights"].append({
                            "name": actor.get_name(),
                            "type": actor.get_class().get_name()
                        })
                except Exception:
                    continue

        self.report["summary"]["lights"] = count

    def audit_audio(self):
        unreal.log("Auditor: Scanning audio...")
        assets = self._get_assets_by_type("SoundWave")
        total = len(assets)
        self.report["summary"]["audio"] = total
        if total == 0:
            return

        with unreal.ScopedSlowTask(total, "Auditing Audio...") as task:
            task.make_dialog(True)
            for ad in assets:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    sound = ad.get_asset()
                    if sound is None:
                        continue
                    name = str(ad.asset_name)

                    inline = False
                    try:
                        # Check if loading behavior forces it into RAM instead of streaming
                        loading = sound.get_editor_property("loading_behavior")
                        if str(loading) == "SoundWaveLoadingBehavior.FORCE_INLINE":
                            inline = True
                            self._warn("AUDIO_INLINE", "'{}' is forced inline (loads into RAM). Consider Streaming.".format(name), "Medium")
                    except Exception:
                        pass

                    self.report["audio"].append({
                        "name": name,
                        "inline": inline,
                        "path": str(ad.package_name)
                    })
                except Exception:
                    continue

    def audit_blueprints(self):
        unreal.log("Auditor: Scanning blueprints...")
        assets = self._get_assets_by_type("Blueprint")
        total = len(assets)
        self.report["summary"]["blueprints"] = total
        if total == 0:
            return

        with unreal.ScopedSlowTask(total, "Auditing Blueprints...") as task:
            task.make_dialog(True)
            for ad in assets:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                
                # Note: Deep compilation check via Python is skipped here as it requires 
                # forcing a recompile of all BPs which can freeze the editor or alter states.
                # We just gather them and let the Orphan audit catch unused ones.
                self.report["blueprints"].append({
                    "name": str(ad.asset_name),
                    "path": str(ad.package_name)
                })

    def audit_sequencers(self):
        unreal.log("Auditor: Scanning sequencers...")
        assets = self._get_assets_by_type("LevelSequence")
        total = len(assets)
        self.report["summary"]["sequencers"] = total
        if total == 0:
            return

        with unreal.ScopedSlowTask(total, "Auditing Sequencers...") as task:
            task.make_dialog(True)
            for ad in assets:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                self.report["sequencers"].append({
                    "name": str(ad.asset_name),
                    "path": str(ad.package_name)
                })

    def audit_orphans(self):
        """Find project assets with zero referencers."""
        unreal.log("Auditor: Scanning for orphan assets...")
        ar_filter = unreal.ARFilter(
            package_paths=["/Game"],
            recursive_paths=True
        )
        assets = self.asset_reg.get_assets(ar_filter)
        total = len(assets)
        if total == 0:
            return

        dep_opts = unreal.AssetRegistryDependencyOptions(
            include_hard_package_references=True,
            include_soft_package_references=True,
            include_hard_management_references=False,
            include_soft_management_references=False
        )

        with unreal.ScopedSlowTask(total, "Scanning for orphan assets...") as task:
            task.make_dialog(True)
            for ad in assets:
                if task.should_cancel():
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    refs = self.asset_reg.get_referencers(str(ad.package_name), dep_opts)
                    if len(refs) == 0:
                        self._warn("ORPHAN", "'{}' has no references.".format(ad.asset_name), "Low")
                except Exception:
                    continue

    def audit_environment(self):
        """Audit PostProcessVolumes and ExponentialHeightFog actors."""
        unreal.log("Auditor: Scanning environment actors...")
        actors = unreal.EditorLevelLibrary.get_all_level_actors()

        for actor in actors:
            try:
                class_name = actor.get_class().get_name()

                if class_name == "PostProcessVolume":
                    # Check if unbounded (affects entire level)
                    unbounded = False
                    try:
                        unbounded = actor.get_editor_property("unbound")
                    except Exception:
                        pass
                    self.report["environment"].append({
                        "name": actor.get_name(),
                        "type": "PostProcessVolume",
                        "unbounded": unbounded
                    })

                elif class_name == "ExponentialHeightFog":
                    vol_fog = False
                    try:
                        fog_comp = actor.get_editor_property("component")
                        if fog_comp:
                            vol_fog = fog_comp.get_editor_property("volumetric_fog")
                    except Exception:
                        pass
                    self.report["environment"].append({
                        "name": actor.get_name(),
                        "type": "ExponentialHeightFog",
                        "volumetric_fog": vol_fog
                    })
                    if vol_fog:
                        self._warn("FOG_VOLUMETRIC", "'{}' has Volumetric Fog enabled (high GPU cost).".format(actor.get_name()), "Medium")

            except Exception:
                continue

    # ------------------------------------------------------------------
    # Save JSON + HTML Dashboard
    # ------------------------------------------------------------------

    def save(self):
        base = "Audit_{}_{}".format(self.scene_name, self.version)
        json_path = os.path.join(self.reports_dir, base + ".json")
        html_path = os.path.join(self.reports_dir, base + ".html")

        # Save JSON
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, indent=4, ensure_ascii=False)
            unreal.log("Auditor: JSON saved -> {}".format(json_path))
        except Exception as exc:
            unreal.log_error("Auditor: Failed to save JSON: {}".format(exc))

        # Generate HTML Dashboard
        try:
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.html")
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()

            html = template.replace("{{SCENE}}", self.scene_name)
            html = html.replace("{{VERSION}}", self.version)
            html = html.replace("{{TIMESTAMP}}", self.report["timestamp"])
            html = html.replace("{{JSON_DATA}}", json.dumps(self.report, ensure_ascii=False))

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            unreal.log("Auditor: Dashboard saved -> {}".format(html_path))
        except Exception as exc:
            unreal.log_error("Auditor: Failed to save HTML: {}".format(exc))

        # Confirmation popup
        try:
            unreal.EditorDialog.show_message(
                "Audit Complete",
                "Report saved to:\n{}\n\nDashboard:\n{}\n\nWarnings: {}".format(
                    json_path, html_path, self.report["summary"]["warnings"]
                ),
                unreal.AppMsgType.OK
            )
        except Exception:
            unreal.log("Auditor: Popup unavailable, files were saved.")


# ======================================================================
# Entry point
# ======================================================================

def run():
    auditor = UEAssetAuditorDB()
    auditor.audit_meshes()
    auditor.audit_textures()
    auditor.audit_materials()
    auditor.audit_lights()
    auditor.audit_environment()
    auditor.audit_audio()
    auditor.audit_blueprints()
    auditor.audit_sequencers()
    auditor.audit_orphans()
    auditor.save()


run()
