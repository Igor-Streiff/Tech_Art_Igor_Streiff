# Portabilidad a Blender (y otros DCC)

Análisis de qué tan reutilizable es esta tool fuera de Maya.

## TL;DR

El **núcleo es 100% portable**: toda la lógica de naming es Python estándar sin
dependencia de Maya. Para correr en Blender solo hace falta una **capa de I/O**
(`blender_ops.py`, ya incluida) que lee/renombra usando `bpy` en vez de
`maya.cmds`. La única decisión de diseño real es de **convención**, no técnica:
Blender prefiere el lado como sufijo `.L`/`.R`.

## Arquitectura: qué se reutiliza y qué no

```
┌─────────────────────────────────────────────┐
│  NÚCLEO PORTABLE (Python puro, sin DCC)       │
│  conventions.py  naming.py  core.py  display  │  ← se reutiliza tal cual
└─────────────────────────────────────────────┘
            ▲                         ▲
            │                         │
   ┌────────────────┐        ┌────────────────────┐
   │  maya_ops.py   │        │  blender_ops.py    │   ← capa de I/O por DCC
   │  (maya.cmds)   │        │  (bpy)             │
   └────────────────┘        └────────────────────┘
```

| Módulo | Depende de | ¿Portable? |
|--------|-----------|------------|
| `conventions.py` | nada | ✅ total |
| `naming.py` | stdlib (`re`, `dataclasses`) | ✅ total |
| `core.py` | `naming` | ✅ total |
| `display.py` | nada | ✅ total |
| `logger_setup.py` | stdlib (`logging`) | ✅ total |
| `maya_ops.py` | `maya.cmds` | ❌ solo Maya |
| `blender_ops.py` | `bpy` | ❌ solo Blender |

La regla del entregable (lógica en funciones, interfaz solo dispara) es lo que
hace esto posible: planificar/validar/mostrar no toca el DCC; solo `*_ops.py`
escribe en la escena.

## Diferencias de API (mismas operaciones)

| Operación | Maya (`maya.cmds`) | Blender (`bpy`) |
|-----------|--------------------|-----------------|
| Listar nodos | `cmds.listRelatives(..., type="transform")` | `armature.data.bones` / `obj.children_recursive` |
| Existe nodo | `cmds.objExists(name)` | `bpy.data.objects.get(name)` |
| Renombrar | `cmds.rename(old, new)` | `bone.name = new` (en EDIT) / `obj.name = new` |
| Tipo de nodo | `cmds.nodeType(node)` | `obj.type`, `bone` vs objeto |
| Curvas anim | `cmds.ls(type="animCurve")` | `obj.animation_data.action.fcurves` |

## La diferencia que sí importa: lado como sufijo `.L`/`.R`

- **Maya / mGear / este renamer (canónico):** el lado va en el medio →
  `hero_L_hand_CTL`.
- **Blender:** sus herramientas de **simetría / X-Mirror / Symmetrize** esperan
  el lado como **sufijo con punto** → `hero_hand_CTL.L`.

Por eso `blender_ops.py` incluye `to_blender_symmetry_name()`, que convierte el
canónico a estilo Blender moviendo el lado al final:

```text
hero_L_hand_CTL   ->  hero_hand_CTL.L
hero_R_arm_fk_CTL ->  hero_arm_fk_CTL.R
hero_C_spine_CTL  ->  hero_spine_CTL      (center sin sufijo)
```

Recomendación: mantener el **canónico con `_L_`** para consistencia cross-DCC y
aplicar la conversión `.L/.R` solo al escribir en Blender si se quiere usar su
simetría nativa. Es un flag de salida, no un cambio del parser.

## Caveats al renombrar en Blender

- **Vertex groups:** renombrar un hueso **no** renombra automáticamente el
  vertex group del skin con su nombre. Si el rig ya tiene piel, hay que
  renombrar los grupos en paralelo (o usar el operador de Blender).
- **Drivers / constraints / fcurves:** Blender suele remapear estas referencias
  al renombrar en EDIT mode; igual conviene validar tras `--apply`.
- **Modo:** renombrar huesos requiere entrar a EDIT mode; `blender_ops` lo hace
  y restaura el modo previo.
- **`.001` de Blender:** Blender agrega sufijos `.001` ante colisiones; el plan
  ya detecta colisiones antes de aplicar, así que esto no debería dispararse.

## Cómo correrlo en Blender

```python
# En el Scripting workspace de Blender, con el paquete en el PYTHONPATH:
import sys; sys.path.append(r"<.../RigRenamer_Tool>")
from rig_renamer.core import build_rename_plan
from rig_renamer import blender_ops

names = blender_ops.collect_bone_names("Armature")
plan, summary = build_rename_plan(names, character="hero", target_types=frozenset({"CTL", "JNT"}))
print(summary)                      # dry-run: revisar antes de aplicar
# blender_ops.apply_bone_rename_plan("Armature", plan, logger)
```

## Otros DCC

El mismo patrón sirve para **Unreal** (control rig / `unreal` API), **Houdini**
(`hou`), **3ds Max** (`pymxs`) o un **renamer de archivos** en disco: escribir un
`<dcc>_ops.py` con `collect_*` y `apply_*`, y reutilizar el núcleo sin cambios.
