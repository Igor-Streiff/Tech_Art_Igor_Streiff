"""Tests del bootstrap Maya (funciones puras, sin Maya)."""

import unittest

from rig_renamer.maya_bootstrap import (
    _is_our_shelf_button_block,
    _strip_shelf_buttons_from_mel,
    filter_assembly_candidates,
    is_valid_tool_root,
    parse_mod_root,
    pick_rig_candidate,
    root_from_script_path,
    shelf_command_source,
    tool_root,
)


class BootstrapPureTests(unittest.TestCase):
    def test_tool_root_points_to_project(self):
        root = tool_root()
        self.assertTrue((root / "rig_renamer.py").is_file())
        self.assertTrue((root / "rig_renamer" / "maya_bootstrap.py").is_file())

    def test_filter_skips_default_cameras(self):
        assemblies = ["persp", "Group", "top", "hero_rig"]
        self.assertEqual(filter_assembly_candidates(assemblies), ["Group", "hero_rig"])

    def test_pick_single_candidate(self):
        self.assertEqual(pick_rig_candidate(["Group"], {}), "Group")

    def test_pick_largest_by_descendant_count(self):
        picked = pick_rig_candidate(
            ["small_grp", "big_rig"],
            {"small_grp": 3, "big_rig": 120},
        )
        self.assertEqual(picked, "big_rig")

    def test_shelf_command_is_path_independent(self):
        cmd = shelf_command_source()
        self.assertIn("RigRenamerShelf", cmd)
        self.assertIn("from rig_renamer.maya_ui import show", cmd)
        self.assertIn("rigRenamerToolRoot", cmd)
        # No debe embeber ninguna ruta absoluta concreta.
        self.assertNotIn(":/", cmd)

    def test_root_from_install_script(self):
        root = tool_root()
        install = root / "install_maya.py"
        self.assertEqual(root_from_script_path(install), root)

    def test_parse_mod_root(self):
        text = "+ RigRenamer 1.0 C:/tools/RigRenamer_Tool\nscripts: .\n"
        self.assertEqual(parse_mod_root(text), "C:/tools/RigRenamer_Tool")

    def test_is_valid_tool_root(self):
        self.assertTrue(is_valid_tool_root(tool_root()))

    def test_drag_installer_exists_and_defines_hook(self):
        drag_file = tool_root() / "drag_to_install_maya.py"
        self.assertTrue(drag_file.is_file())
        text = drag_file.read_text(encoding="utf-8")
        self.assertIn("def onMayaDroppedPythonFile", text)

    def test_drag_uninstaller_exists_and_defines_hook(self):
        drag_file = tool_root() / "drag_to_uninstall_maya.py"
        self.assertTrue(drag_file.is_file())
        text = drag_file.read_text(encoding="utf-8")
        self.assertIn("def onMayaDroppedPythonFile", text)

    def test_uninstaller_entry_exists(self):
        self.assertTrue((tool_root() / "uninstall_maya.py").is_file())


class ShelfScrubTests(unittest.TestCase):
    def test_strip_removes_our_button_by_label(self):
        mel = (
            'shelfButton\n    -label "Rig Renamer"\n    -command "x"\n;\n'
            'shelfButton\n    -label "Other"\n    -command "y"\n;\n'
        )
        updated, count = _strip_shelf_buttons_from_mel(mel)
        self.assertEqual(count, 1)
        self.assertIn("Other", updated)
        self.assertNotIn("Rig Renamer", updated)

    def test_strip_matches_by_command_marker(self):
        mel = (
            'shelfButton\n    -label "X"\n'
            '    -command "# RigRenamerShelf\\nshow()"\n;\n'
        )
        _, count = _strip_shelf_buttons_from_mel(mel)
        self.assertEqual(count, 1)

    def test_strip_keeps_unrelated_buttons(self):
        mel = 'shelfButton\n    -label "Nada"\n    -command "print(1)"\n;\n'
        updated, count = _strip_shelf_buttons_from_mel(mel)
        self.assertEqual(count, 0)
        self.assertEqual(updated, mel)

    def test_block_detection(self):
        self.assertTrue(_is_our_shelf_button_block('-label "Rig Renamer"'))
        self.assertTrue(_is_our_shelf_button_block("from rig_renamer import x"))
        self.assertFalse(_is_our_shelf_button_block('-label "Otro"'))


if __name__ == "__main__":
    unittest.main()
