import unreal
import json
import os
import re
import datetime


class UEAssetAuditorDB:
    """
    Asset inventory and basic configuration review for Unreal Engine 5.
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
            "partial": False,
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

    def _warn(self, tag, message, priority="Low"):
        self.report["warnings"].append({
            "tag": tag,
            "msg": message,
            "priority": priority
        })
        self.report["summary"]["warnings"] += 1

    def _unavailable(self, name, field, exc):
        self.report["partial"] = True
        self._warn("READ_ERROR", "'{}': {} unavailable; see Unreal log.".format(name, field))
        unreal.log_warning("Auditor: {} / {}: {}".format(name, field, exc))

    def _read(self, name, field, getter):
        """Keep an unavailable property distinct from a measured zero or False."""
        try:
            value = getter()
            if value is None:
                raise ValueError("No value returned")
            return value
        except Exception as exc:
            self._unavailable(name, field, exc)
            return None

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
                    self.report["partial"] = True
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    mesh = ad.get_asset()
                    if mesh is None:
                        self._unavailable(str(ad.asset_name), "asset loading", "Asset could not be loaded")
                        continue
                    name = str(ad.asset_name)
                    num_lods = self._read(name, "LOD count", lambda: mesh.get_num_lods())
                    nanite_on = self._read(name, "Nanite setting",
                                           lambda: mesh.get_editor_property("nanite_settings").enabled)
                    mat_slots = self._read(name, "material slots", lambda: len(mesh.static_materials))

                    def collision_setting():
                        body_setup = mesh.get_editor_property("body_setup")
                        if body_setup is None:
                            return False
                        flag = body_setup.get_editor_property("collision_trace_flag")
                        if flag is None:
                            raise ValueError('Collision flag unavailable')
                        return flag == unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE

                    complex_as_simple = self._read(name, "collision setting", collision_setting)
                    vertices = self._read(name, "LOD 0 vertices", lambda: mesh.get_num_vertices(0))
                    triangles = self._read(name, "LOD 0 triangles", lambda: mesh.get_num_triangles(0))

                    # Warnings
                    if nanite_on is False and num_lods is not None and num_lods < 3:
                        self._warn("MESH_LOD", "'{}': Nanite off and fewer than 3 LODs; review for intended use.".format(name), "Low")
                    if mat_slots is not None and mat_slots > 5:
                        self._warn("MESH_SLOTS", "'{}': {} material slots exceed the review threshold of 5.".format(name, mat_slots), "Low")
                    if triangles is not None and triangles > high_poly_threshold:
                        self._warn("MESH_HEAVY", "'{}': {:,} LOD 0 triangles exceed the review threshold of {:,}; runtime cost not measured.".format(name, triangles, high_poly_threshold), "Low")
                    if complex_as_simple:
                        self._warn("MESH_COLLISION", "'{}': Complex Collision as Simple is configured; review collision usage.".format(name), "Low")

                    self.report["meshes"].append({
                        "name": name,
                        "vertices": vertices,
                        "triangles": triangles,
                        "lods": num_lods,
                        "nanite": nanite_on,
                        "complex_collision": complex_as_simple,
                        "material_slots": mat_slots,
                        "path": str(ad.package_name)
                    })
                except Exception as exc:
                    self._unavailable(str(ad.asset_name), "asset inspection", exc)

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
                    self.report["partial"] = True
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    tex = ad.get_asset()
                    if tex is None:
                        self._unavailable(str(ad.asset_name), "asset loading", "Asset could not be loaded")
                        continue
                    name = str(ad.asset_name)
                    w = self._read(name, "texture width", lambda: tex.blueprint_get_size_x())
                    h = self._read(name, "texture height", lambda: tex.blueprint_get_size_y())

                    if (w is not None and w > max_res) or (h is not None and h > max_res):
                        self._warn("TEX_LARGE", "'{}': {}x{} exceeds the review threshold of {} px; memory usage not measured.".format(name, w if w is not None else "N/A", h if h is not None else "N/A", max_res), "Low")

                    self.report["textures"].append({
                        "name": name,
                        "width": w,
                        "height": h,
                        "path": str(ad.package_name)
                    })
                except Exception as exc:
                    self._unavailable(str(ad.asset_name), "asset inspection", exc)

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
                    self.report["partial"] = True
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    mat = ad.get_asset()
                    if mat is None:
                        self._unavailable(str(ad.asset_name), "asset loading", "Asset could not be loaded")
                        continue
                    name = str(ad.asset_name)
                    blend = self._read(name, "blend mode", lambda: mat.get_editor_property("blend_mode"))

                    if blend == unreal.BlendMode.BLEND_TRANSLUCENT:
                        self._warn("MAT_TRANSLUCENT", "'{}': translucent blend mode; review its use in the scene.".format(name), "Low")

                    self.report["materials"].append({
                        "name": name,
                        "blend_mode": str(blend) if blend is not None else None,
                        "path": str(ad.package_name)
                    })
                except Exception as exc:
                    self._unavailable(str(ad.asset_name), "asset inspection", exc)
                    continue

    def audit_lights(self):
        unreal.log("Auditor: Scanning lights...")
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        count = 0

        with unreal.ScopedSlowTask(len(actors), "Auditing Lights...") as task:
            task.make_dialog(True)
            for actor in actors:
                if task.should_cancel():
                    self.report["partial"] = True
                    break
                task.enter_progress_frame(1, actor.get_name())
                try:
                    if isinstance(actor, unreal.Light):
                        count += 1
                        self.report["lights"].append({
                            "name": actor.get_name(),
                            "type": actor.get_class().get_name()
                        })
                except Exception as exc:
                    self._unavailable(actor.get_name(), "actor inspection", exc)
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
                    self.report["partial"] = True
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    sound = ad.get_asset()
                    if sound is None:
                        self._unavailable(str(ad.asset_name), "asset loading", "Asset could not be loaded")
                        continue
                    name = str(ad.asset_name)

                    loading = self._read(name, "loading behavior", lambda: sound.get_editor_property("loading_behavior"))
                    inline = (loading == unreal.SoundWaveLoadingBehavior.FORCE_INLINE) if loading is not None else None
                    if inline:
                        self._warn("AUDIO_INLINE", "'{}': Force Inline is configured; review audio loading needs.".format(name))

                    self.report["audio"].append({
                        "name": name,
                        "inline": inline,
                        "path": str(ad.package_name)
                    })
                except Exception as exc:
                    self._unavailable(str(ad.asset_name), "asset inspection", exc)
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
                    self.report["partial"] = True
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                
                # Note: Deep compilation check via Python is skipped here as it requires 
                # forcing a recompile of all BPs which can freeze the editor or alter states.
                # This module only inventories Blueprint assets.
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
                    self.report["partial"] = True
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                self.report["sequencers"].append({
                    "name": str(ad.asset_name),
                    "path": str(ad.package_name)
                })

    def audit_orphans(self):
        """List assets with no detected package referencers; not a deletion recommendation."""
        unreal.log("Auditor: Checking registered package referencers...")
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

        with unreal.ScopedSlowTask(total, "Checking package referencers...") as task:
            task.make_dialog(True)
            for ad in assets:
                if task.should_cancel():
                    self.report["partial"] = True
                    break
                task.enter_progress_frame(1, str(ad.asset_name))
                try:
                    refs = self.asset_reg.get_referencers(str(ad.package_name), dep_opts)
                    if len(refs) == 0:
                        self._warn("ORPHAN", "'{}': no hard/soft package referencers detected; this does not prove the asset is unused.".format(ad.asset_name), "Low")
                except Exception as exc:
                    self._unavailable(str(ad.asset_name), "asset inspection", exc)
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
                    unbounded = self._read(actor.get_name(), "unbounded setting",
                                           lambda: actor.get_editor_property("unbound"))
                    self.report["environment"].append({
                        "name": actor.get_name(),
                        "type": "PostProcessVolume",
                        "unbounded": unbounded
                    })

                elif class_name == "ExponentialHeightFog":
                    vol_fog = self._read(actor.get_name(), "volumetric fog setting",
                                         lambda: actor.get_editor_property("component").get_editor_property("volumetric_fog"))
                    self.report["environment"].append({
                        "name": actor.get_name(),
                        "type": "ExponentialHeightFog",
                        "volumetric_fog": vol_fog
                    })
                    if vol_fog:
                        self._warn("FOG_VOLUMETRIC", "'{}': Volumetric Fog is enabled; runtime cost not measured.".format(actor.get_name()), "Low")

            except Exception as exc:
                self._unavailable(actor.get_name(), "actor inspection", exc)
                continue

    # ------------------------------------------------------------------
    # Save JSON + HTML Dashboard
    # ------------------------------------------------------------------

    def save(self):
        # Counts describe recorded entries, including after a cancelled/partial scan.
        for category in ("meshes", "textures", "materials", "lights", "audio", "blueprints", "sequencers"):
            self.report["summary"][category] = len(self.report[category])
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
                "Asset Inventory",
                "Report output:\n{}\n\nDashboard:\n{}\n\nReview notes: {}".format(
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
