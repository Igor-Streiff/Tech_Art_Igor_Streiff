"""Tests de validación y frenado ante errores."""

import unittest

from rig_renamer.core import build_rename_plan
from rig_renamer.validate import (
    detect_foreign_character_prefix,
    is_canonical_for_character,
    normalize_character,
    validate_character,
)


class ValidateCharacterTests(unittest.TestCase):
    def test_normalize_lowercase(self):
        self.assertEqual(normalize_character(" Jinx "), "jinx")

    def test_reject_empty(self):
        with self.assertRaises(ValueError):
            validate_character("   ")

    def test_reject_invalid_chars(self):
        with self.assertRaises(ValueError):
            validate_character("jinx-rig")


class ForeignPrefixTests(unittest.TestCase):
    def test_detects_other_character_prefix(self):
        foreign = detect_foreign_character_prefix("hero_C_master_CTL", "jinx")
        self.assertEqual(foreign, "hero")

    def test_ignores_same_character_prefix(self):
        foreign = detect_foreign_character_prefix("jinx_C_master_CTL", "jinx")
        self.assertIsNone(foreign)


class IdempotencyTests(unittest.TestCase):
    def test_canonical_name_is_skipped(self):
        self.assertTrue(is_canonical_for_character("jinx_L_hand_CTL", "jinx"))
        self.assertTrue(is_canonical_for_character("jinx_L_hand_CTL", "Jinx"))

    def test_case_insensitive_character_output(self):
        from rig_renamer.naming import propose_name

        self.assertEqual(propose_name("Jinx", "hand_l_ctrl"), "jinx_L_hand_CTL")


class BlockerTests(unittest.TestCase):
    def test_foreign_prefix_blocks_plan(self):
        _, summary = build_rename_plan(["hero_C_master_CTL", "god_ctrl"], "jinx")
        self.assertTrue(summary.blockers)
        self.assertFalse(summary.safe_to_apply)

    def test_messy_names_still_plan_without_blockers(self):
        _, summary = build_rename_plan(["god_ctrl", "hand_l_ctrl"], "jinx")
        self.assertFalse(summary.blockers)
        self.assertEqual(summary.planned, 2)


if __name__ == "__main__":
    unittest.main()
