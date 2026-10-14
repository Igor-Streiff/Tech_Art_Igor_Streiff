"""Tests del parser de naming (cobertura ampliada de variantes de rig)."""

import unittest

from rig_renamer.core import build_rename_plan
from rig_renamer.naming import parse_control_name, propose_name


class SideTests(unittest.TestCase):
    def test_english_aliases(self):
        self.assertEqual(propose_name("hero", "hand_l_ctrl"), "hero_L_hand_CTL")
        self.assertEqual(propose_name("hero", "lf_arm_control"), "hero_L_arm_CTL")
        self.assertEqual(propose_name("hero", "rt_foot_CON"), "hero_R_foot_CTL")

    def test_spanish_aliases(self):
        self.assertEqual(propose_name("hero", "mano_izq_ctrl"), "hero_L_mano_CTL")
        self.assertEqual(propose_name("hero", "pie_der_ctrl"), "hero_R_pie_CTL")
        self.assertEqual(propose_name("hero", "izquierda_brazo_ctl"), "hero_L_brazo_CTL")

    def test_center_default(self):
        self.assertEqual(propose_name("hero", "spine_ctrl"), "hero_C_spine_CTL")
        self.assertEqual(propose_name("hero", "c_cog_ctrl"), "hero_C_cog_CTL")


class TypeAndSkipTests(unittest.TestCase):
    def test_joints_and_geo_are_skipped_by_default(self):
        self.assertIsNone(propose_name("hero", "L_arm_JNT"))
        self.assertIsNone(propose_name("hero", "root_grp"))
        self.assertIsNone(propose_name("hero", "body_GEO"))
        self.assertIsNone(propose_name("hero", "spine_01"))

    def test_camel_case_suffix(self):
        self.assertEqual(propose_name("hero", "L_handFkCtrl"), "hero_L_hand_fk_CTL")

    def test_namespace_and_dag_path(self):
        self.assertEqual(
            propose_name("hero", "rig:grp|L_hand_ctrl"), "hero_L_hand_CTL"
        )


class DescriptorTests(unittest.TestCase):
    def test_fk_ik_pole(self):
        self.assertEqual(propose_name("hero", "L_arm_fk_ctrl"), "hero_L_arm_fk_CTL")
        self.assertEqual(propose_name("hero", "L_arm_ik_ctrl"), "hero_L_arm_ik_CTL")
        self.assertEqual(propose_name("hero", "L_arm_pv_ctrl"), "hero_L_arm_pole_CTL")

    def test_master_global(self):
        self.assertEqual(propose_name("hero", "global_ctrl"), "hero_C_global_CTL")
        self.assertEqual(propose_name("hero", "god_ctrl"), "hero_C_master_CTL")

    def test_connectors_props(self):
        self.assertEqual(
            propose_name("hero", "R_hand_prop_ctrl"), "hero_R_hand_prop_CTL"
        )
        self.assertEqual(
            propose_name("hero", "weapon_socket_CON"), "hero_C_weapon_socket_CTL"
        )
        self.assertEqual(
            propose_name("hero", "L_hand_attach_ctrl"), "hero_L_hand_attach_CTL"
        )


class SpecialAnatomyTests(unittest.TestCase):
    def test_tail_chain(self):
        self.assertEqual(propose_name("dragon", "tail_03_ctrl"), "dragon_C_tail_03_CTL")
        self.assertEqual(
            propose_name("dragon", "tail_dyn_ctrl"), "dragon_C_tail_dyn_CTL"
        )

    def test_wings(self):
        self.assertEqual(
            propose_name("dragon", "L_wing_tip_ctrl"), "dragon_L_wing_tip_CTL"
        )
        self.assertEqual(
            propose_name("dragon", "wing_upper_R_CON"), "dragon_R_wing_upper_CTL"
        )

    def test_quadruped(self):
        self.assertEqual(
            propose_name("wolf", "front_L_hock_ctrl"), "wolf_L_hock_front_CTL"
        )
        self.assertEqual(
            propose_name("wolf", "hind_paw_R_ctrl"), "wolf_R_paw_back_CTL"
        )


class FaceTests(unittest.TestCase):
    def test_brow_lid(self):
        self.assertEqual(
            propose_name("hero", "L_brow_inner_ctrl"), "hero_L_brow_inner_CTL"
        )
        self.assertEqual(propose_name("hero", "lid_up_L_ctrl"), "hero_L_lid_upper_CTL")

    def test_texture_joystick_without_suffix(self):
        self.assertEqual(
            propose_name("hero", "face_texSwap_joystick"),
            "hero_C_face_tex_selector_joystick_CTL",
        )
        self.assertEqual(
            propose_name("hero", "eyeColor_selector"),
            "hero_C_eye_color_selector_CTL",
        )


class JointTargetTests(unittest.TestCase):
    JOINTS = frozenset({"JNT"})
    BOTH = frozenset({"CTL", "JNT"})

    def test_joint_renamed_when_targeted(self):
        self.assertEqual(
            propose_name("hero", "L_upperArm_jnt", target_types=self.JOINTS),
            "hero_L_arm_upper_JNT",
        )
        self.assertEqual(
            propose_name("hero", "spine_01_jnt", target_types=self.JOINTS),
            "hero_C_spine_01_JNT",
        )

    def test_control_skipped_when_only_joints_targeted(self):
        self.assertIsNone(
            propose_name("hero", "L_hand_ctrl", target_types=self.JOINTS)
        )

    def test_both_types_together(self):
        self.assertEqual(
            propose_name("hero", "L_hand_ctrl", target_types=self.BOTH),
            "hero_L_hand_CTL",
        )
        self.assertEqual(
            propose_name("hero", "L_hand_jnt", target_types=self.BOTH),
            "hero_L_hand_JNT",
        )

    def test_plan_includes_joints(self):
        from rig_renamer.core import build_rename_plan

        plan, summary = build_rename_plan(
            ["L_hand_ctrl", "L_hand_jnt", "root_grp"],
            "hero",
            target_types=self.BOTH,
        )
        self.assertEqual(plan["L_hand_ctrl"], "hero_L_hand_CTL")
        self.assertEqual(plan["L_hand_jnt"], "hero_L_hand_JNT")
        self.assertEqual(summary.skipped, 1)


class PlanTests(unittest.TestCase):
    def test_already_canonical_is_idempotent(self):
        names = [
            "hero_L_hand_CTL",
            "hero_L_arm_fk_CTL",
            "hero_C_spine_01_CTL",
            "hero_L_brow_inner_CTL",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(propose_name("hero", name), name)

    def test_already_canonical_skipped_in_plan(self):
        plan, summary = build_rename_plan(["hero_L_arm_CTL"], "hero")
        self.assertEqual(plan, {})
        self.assertEqual(summary.skipped, 1)

    def test_collision_detected(self):
        plan, summary = build_rename_plan(["hand_l_ctrl", "L_hand_CTL"], "hero")
        self.assertTrue(summary.collisions)


class BlenderSymmetryTests(unittest.TestCase):
    def test_side_moves_to_suffix(self):
        from rig_renamer.blender_ops import to_blender_symmetry_name

        self.assertEqual(to_blender_symmetry_name("hero_L_hand_CTL"), "hero_hand_CTL.L")
        self.assertEqual(
            to_blender_symmetry_name("hero_R_arm_fk_CTL"), "hero_arm_fk_CTL.R"
        )

    def test_center_has_no_suffix(self):
        from rig_renamer.blender_ops import to_blender_symmetry_name

        self.assertEqual(to_blender_symmetry_name("hero_C_spine_CTL"), "hero_spine_CTL")


if __name__ == "__main__":
    unittest.main()
