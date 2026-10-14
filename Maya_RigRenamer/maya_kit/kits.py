"""Registro de rigs de prueba locales.

La escena de cada rig NO vive dentro de la tool (que es portable y se publica):
vive en tu carpeta de práctica. Cada kit apunta ahí con `scenes_dir_rel`.

Para agregar un personaje nuevo: dejá su .ma en tu carpeta de práctica, definí
un RigDemoKit acá con la ruta relativa correcta y registralo en KITS. La tool en
sí no cambia.
"""

from __future__ import annotations

from maya_kit.scene_prep import RigDemoKit

JINX = RigDemoKit(
    character="jinx",
    top_group="Group",
    # Carpeta de práctica (fuera de la tool), relativa a la raíz de la tool.
    scenes_dir_rel="../ENTREGAS_semana05/Practica_RigRenamer_Jinx",
    clean_filename="Jinx Rig.ma",
    messy_filename="Jinx Rig_messy.ma",
    # FK visibles → nombres sucios mezclados (EN/ES) que el parser sabe normalizar.
    messy_map={
        "FKHip_R": "rt_hip_control",
        "FKHip_L": "hand_l_ctrl",
        "FKKnee_R": "pie_der_ctrl",
        "FKKnee_L": "lf_knee_CON",
        "FKAnkle_R": "R_foot_ctrl",
        "FKAnkle_L": "mano_izq_ctrl",
        "FKToes_R": "foot_LFT_ctrl",
        "FKToes_L": "izq_toe_control",
        "FKNeck_M": "spine_ctrl",
        "FKHead_M": "god_ctrl",
        "FKJaw_M": "jaw_M_ctrl",
    },
)

# Clave (lowercase) → kit. Agregá más personajes aquí.
KITS: dict[str, RigDemoKit] = {
    "jinx": JINX,
}


def get_kit(name: str) -> RigDemoKit:
    key = name.strip().lower()
    if key not in KITS:
        disponibles = ", ".join(sorted(KITS)) or "(ninguno)"
        raise KeyError(f"No hay kit '{name}'. Disponibles: {disponibles}.")
    return KITS[key]
