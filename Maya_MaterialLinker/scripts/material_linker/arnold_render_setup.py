"""
Arnold render prep helper (post Material Linker) — TAR-024 / Removing Noise workflow.

Run in Maya after linking textures:

    import arnold_render_setup
    arnold_render_setup.apply_checklist()
"""

from __future__ import annotations

try:
    import maya.cmds as cmds
    import mtoa.core as core
except ImportError:
    cmds = None
    core = None

AOV_LIST = (
    ("diffuse", "RGBA"),
    ("specular", "RGBA"),
    ("transmission", "RGBA"),
    ("sss", "RGBA"),
    ("coat", "RGBA"),
    ("emission", "RGBA"),
    ("volume", "RGBA"),
    ("shadow", "RGBA"),
    ("direct_diffuse", "RGBA"),
    ("indirect_diffuse", "RGBA"),
)


def _require_maya():
    if cmds is None:
        raise RuntimeError("arnold_render_setup must run inside Maya with MtoA loaded.")


def ensure_arnold_renderer():
    _require_maya()
    if cmds.getAttr("defaultRenderGlobals.currentRenderer") != "arnold":
        cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
        print("Renderer set to Arnold.")


def enable_aovs():
    _require_maya()
    ensure_arnold_renderer()
    try:
        import mtoa.aovs as aovs
    except ImportError:
        print("WARNING: mtoa.aovs not available — enable AOVs manually in Render Settings.")
        return

    for name, channels in AOV_LIST:
        try:
            if not aovs.isAOVEnabled(name):
                aovs.addAOV(name)
            print(f"  AOV enabled: {name}")
        except Exception as exc:
            print(f"  AOV skip {name}: {exc}")


def print_noise_workflow():
    text = """
=== Arnold noise workflow (FormacionTechArt_Arnold_Removing_Noise) ===

1. Render AOVs — isolate diffuse, specular, sss, transmission, alpha.
2. Identify noise — check WHICH AOV is noisy (that tells you which sample to raise).
3. Raise ONLY that sample (not global AA first):
   - Diffuse noise        -> diffuse_samples
   - Specular noise       -> specular_samples
   - Transmission noise   -> transmission_samples
   - SSS noise            -> sss_samples
   - Motion blur / DOF    -> camera (AA) samples (expensive: squared cost)
   - Shadow noise         -> light samples (3-4 is often enough)
4. Re-render and compare render time vs quality.

IPR checklist after Material Linker:
  [ ] Viewport / IPR set to Arnold
  [ ] Normal maps: file node color space = Raw
  [ ] BaseColor / Emissive: sRGB
  [ ] Roughness / Metalness: Raw
  [ ] No pink shaders (broken texture paths)
  [ ] Test 1 frame at target resolution before final batch
"""
    print(text)
    return text


def apply_checklist():
    _require_maya()
    print("=== Arnold Render Setup ===\n")
    ensure_arnold_renderer()
    print("\nEnabling diagnostic AOVs...")
    enable_aovs()
    print_noise_workflow()
    print("Done. Tune samples per noisy AOV, then run final render for TAR-024.")
