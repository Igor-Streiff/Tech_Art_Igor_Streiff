"""Tests del registro de kits de escena (importable sin Maya)."""

import unittest

from maya_kit.kits import KITS, get_kit
from maya_kit.scene_prep import RigDemoKit


class KitRegistryTests(unittest.TestCase):
    def test_jinx_kit_exists(self):
        kit = get_kit("jinx")
        self.assertIsInstance(kit, RigDemoKit)
        self.assertEqual(kit.character, "jinx")
        self.assertEqual(kit.top_group, "Group")

    def test_lookup_is_case_insensitive(self):
        self.assertIs(get_kit("JINX"), get_kit("jinx"))

    def test_unknown_kit_raises(self):
        with self.assertRaises(KeyError):
            get_kit("no_existe")

    def test_paths_point_to_practice_folder(self):
        kit = get_kit("jinx")
        self.assertTrue(
            kit.clean_scene_path().as_posix().endswith(
                "Practica_RigRenamer_Jinx/Jinx Rig.ma"
            )
        )
        self.assertTrue(
            kit.messy_scene_path().as_posix().endswith(
                "Practica_RigRenamer_Jinx/Jinx Rig_messy.ma"
            )
        )

    def test_messy_map_targets_are_parseable(self):
        from rig_renamer.naming import propose_name

        kit = get_kit("jinx")
        for messy_name in kit.messy_map.values():
            self.assertIsNotNone(
                propose_name(kit.character, messy_name),
                msg=f"'{messy_name}' debería ser reconocido como control",
            )


if __name__ == "__main__":
    unittest.main()
