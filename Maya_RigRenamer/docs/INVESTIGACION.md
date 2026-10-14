# Investigación — variantes de naming en rigs de personaje

Base para la taxonomía de `rig_renamer/conventions.py`. Objetivo: que el renamer
**reconozca** la mayor cantidad de convenciones reales (no inventadas) para no
omitir ni mutilar controles. Recopilado de fuentes de industria (junio 2026).

## Formato canónico adoptado

Se adopta una variante del estándar de **mGear**
(`{side}_{component}_{description}_{index}_{type}`), con el personaje como prefijo:

```
<character>_<side>_<component>_<position(s)>_<descriptor(s)>_<index>_<TYPE>
```

Ejemplos: `hero_L_arm_fk_CTL`, `hero_C_spine_01_CTL`, `hero_R_paw_back_CTL`.

## 1. Lado (side) → L / R / C

Consenso fuerte: usar **L / R** en mayúscula (no `l`/`left`) por legibilidad y
scripting; **C** para center. Variantes aceptadas como entrada:

| Canónico | Inglés | Español | Abreviaturas |
|----------|--------|---------|--------------|
| L | left, lf, lft, lt | izquierda, izq, izqda, izda | l |
| R | right, rt, rgt | derecha, der, dcha, dch | r |
| C | center, centre, cen, ctr | centro, central | c, cn |

> SeithCG y Ronald Fong recomiendan `L_`/`lf_` sobre `l_` porque la "l" minúscula
> se confunde con "1"/"i" y facilita search & replace. mGear permite redefinir
> los nombres de lado (L/R/C → lf/rt, etc.).

## 2. Tipo de nodo (suffix)

Solo la **familia control** se renombra por default; el resto se detecta para
**omitir** (no tocar joints/geo/grupos).

- **Control (→ CTL):** ctl, ctrl, con, cnt, control, anim, handle
- **No-control (se omiten):** jnt/jt/joint/bnd/bind/skn/def/end (joints),
  grp/gp/ofs/zero/null/srt (grupos), loc (locator), geo/msh/mesh (geometría),
  crv, ikh (IK handle), clt (cluster)

> SeithCG, Ronald Fong (3 letras en mayúscula para selección por wildcard
> `*_CTRL`), Takken.io (ROOT/DEF/MCH/ORG/CTRL/JNT/IK/FK/POLE/STR…).

## 3. Posición (position)

Modificadores que refinan la parte. Inglés + español + abreviaturas:

- Vertical: upper/up/upr/superior/arriba · lower/lo/dn/down/inferior/abajo · top · bottom/bot
- Antero-posterior: front/fr/fore/frontal/anterior · back/bk/hind/rear/posterior/trasero
- Interior/exterior: inner/in/interior · outer/out/exterior
- Medio: mid/middle/medio
- Cadena de dedos: proximal/prox · intermediate/inter · distal/dist · tip · base

> En cuadrúpedos **front/hind** distinguen miembro delantero/trasero → se
> normalizan a posición front/back (Gnomon, Blender front_thigh.L).

## 4. Descriptor (rol / función)

Lo más extenso, porque cubre los casos que el usuario marcó como faltantes.

- **Cinemática:** fk · ik · switch (fkik/ikfk/blend) · pole (pv/upv/upvector)
- **Deformación/refinamiento:** twist · bend · tweak (micro) · stretch · squash · dyn (dynamic)
- **Maestros/jerarquía:** master (god/all) · main · global · world · cog · root
- **Espacios/follow/ajustes/GUI:** space (spaceswitch) · follow · settings (config/options) · gui (panel/ui/picker) · attr (attribute holder)
- **Conectores / props / anclajes (los "plugs"):** socket · attach · plug · connector (conn/cnx) · grip · prop · pickup · weapon (wpn) · anchor · pin
- **GUI facial / joystick (incluye swap de textura estilo anime):** joystick (joy/stick) · slider · pad · selector (select/sel/swap/texswap/textureswap) · aim (look/lookat)

> mGear (space switchers, host de atributos IK/FK), Faceware/MetaHuman
> (CTRL_expressions, sliders/joysticks faciales, FACS), Unity/Unreal/Blender
> (sockets, parent/child-of constraints, grip points para armas — "los plugs").

## 5. Partes anatómicas (component)

Cualquier token desconocido se conserva como parte (cobertura universal). Catálogo
reconocido para reporte/validación:

- **Biped:** root, cog, hip, pelvis, spine, chest, neck, head; clavicle, scapula,
  shoulder, arm, forearm, elbow, wrist, hand, palm; finger, thumb, index, middle,
  ring, pinky, metacarpal; leg, thigh, knee, shin, calf, ankle, foot, heel, toe, ball
- **Cuadrúpedo:** femur, tibia, hock, tarsal, metatarsal, fetlock, paw, claw, hoof, haunch
- **Alas:** wing, feather, patagium, covert
- **Cola / apéndices flexibles:** tail, tentacle, antenna, whisker, fin, horn, tongue, ear, trunk
- **Cara:** eye, iris, pupil, lid/eyelid, brow/eyebrow, cheek, jaw, chin, lip,
  mouth, corner, nose, nostril, teeth, forehead, face

### Sobre los casos que planteó el usuario

| Caso | Cómo lo cubre el renamer |
|------|--------------------------|
| Aliases español (izq, der) | Tabla SIDE_ALIASES (ES/EN/abreviaturas) |
| Plugs / conectores / anclajes | Descriptores socket/attach/plug/connector/grip/anchor/pin |
| Props / armas | Descriptores prop/weapon/pickup |
| Cola flexible / dinámica | Parte `tail` + descriptor `dyn`; índice por segmento (`tail_03`) |
| Cuadrúpedo | Posición front/hind + partes paw/hock/femur/tibia… |
| Alas | Parte `wing`/`feather` + posición upper/mid/tip |
| Joystick facial de swap de textura (anime) | CONTROL_HINTS (joystick/slider/selector/swap) → se reconoce aunque no tenga sufijo `_ctrl` |

## Fuentes consultadas

- SeithCG — Naming conventions: http://seithcg.com/wordpress/?page_id=20
- Ronald Fong — Tips on Naming Conventions in Maya: https://ronald-fong.com/blog/tips-on-naming-conventions-in-maya/
- Charios — Bone-naming mistakes: https://charios.com/blog/bone-naming-mistakes-that-cost-you-an-afternoon
- Tech-Artists.org — Scalable rigging pipeline: https://www.tech-artists.org/t/best-practices-for-setting-up-a-scalable-rigging-pipeline-for-a-small-studio/18075
- mGear Shifter — Naming Rules: https://mgear4.readthedocs.io/en/master/shifterUserDocumentation.html
- Faceware — Rigging best practices (facial): http://support.facewaretech.com/rigging_best_practices
- Speech Graphics — Rigging guidelines (FACS, UI controls): https://docs.speech-graphics.com/en/sgx/4.5/rigging
- Gnomon — Creating a Quadruped Rig for Production: https://www.thegnomonworkshop.com/workshops/creating-a-quadruped-rig-for-production
- Blender 4.4 Manual — Bone naming (L/R, Front/Back): https://docs.blender.org/manual/en/4.4/animation/armatures/bones/editing/naming.html
- Takken.io — Rigging bone naming terms: https://takken.io/notes/blender/rigging/
- MoCap Online — Unity Animation Rigging (sockets, grips): https://mocaponline.com/blogs/mocap-news/unity-animation-rigging-guide
- SWTOR Slicers Wiki — Attaching weapons/objects (constraints): https://github.com/SWTOR-Slicers/WikiPedia/wiki/Attaching-weapons-and-other-objects-to-a-character-with-custom-rigs
