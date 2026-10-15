<a id="english"></a>
# UE Asset Auditor

**Asset inventory and basic review for Unreal Engine.**

*[Español abajo](#español)*

<div align="center">
  <img src="UE_AssetAuditor_banner.png" alt="UE Asset Auditor" width="100%">
</div>

A Python automation exercise developed during the Tech Art course. It gathers asset information and selected level settings, applies simple review rules, and exports a searchable HTML dashboard and JSON report. Its purpose is to make an initial inspection easier to share and review outside the editor.

## Demo

https://github.com/user-attachments/assets/c9fad7df-e1e5-41ee-956e-0126d166bbda

The recording shows the original exercise. The current report presents flags as review notes and displays unavailable properties as **N/A**.

## What It Collects

- **Static meshes:** LOD 0 vertices and triangles, LOD count, Nanite setting, material slots, and collision configuration.
- **Texture2D assets:** dimensions in pixels.
- **Material assets:** blend mode. Material instances are outside this scan.
- **SoundWave assets:** explicit loading behavior, when readable.
- **Blueprints and Level Sequences:** names and package paths; inventory only.
- **Loaded level actors:** lights, PostProcessVolume unbounded setting, and ExponentialHeightFog volumetric-fog setting.
- **Package references:** assets with no detected hard/soft package referencers.

Assets are scanned under **`/Game`**; Engine and plugin content are outside that scope. Actor information covers what is currently loaded in the editor, not every map or unloaded World Partition cell.

## Review Rules

These are prompts for a person to investigate, not measured performance faults or universal production limits.

| Tag | Recorded condition |
|-----|--------------------|
| `MESH_LOD` | Nanite off and fewer than 3 LODs |
| `MESH_HEAVY` | More than 100,000 LOD 0 triangles |
| `MESH_SLOTS` | More than 5 material slots |
| `MESH_COLLISION` | Complex Collision as Simple configured |
| `TEX_LARGE` | A dimension exceeds 2048 px |
| `MAT_TRANSLUCENT` | Translucent blend mode |
| `FOG_VOLUMETRIC` | Volumetric Fog enabled |
| `AUDIO_INLINE` | Force Inline explicitly configured |
| `ORPHAN` | No package referencers detected by this check; **not proof that the asset is unused** |
| `READ_ERROR` | A property or asset could not be inspected; consult the Unreal log |

Thresholds are defaults in the Python methods, not recommended budgets for every asset or platform. No detected referencers is not a deletion recommendation: entry maps, code/configuration loads, and Asset Manager rules require separate review.

**Scope:** this report does not measure frame time, CPU/GPU cost, RAM/VRAM residency, texture streaming pressure, or real-time readiness. Performance diagnosis requires measurements during execution with Unreal's profiling tools. Source ngon topology is not inferred from triangle/vertex counts.

Failed property reads are stored as JSON `null` and shown as **N/A**, keeping them distinct from measured zero and false values. Cancelled scans or unreadable data mark the report **partial**; counts describe the entries actually recorded. Level Sequences are included in JSON; the dashboard shows its existing asset and actor tabs.

## Run in Unreal Editor

1. Enable **Python Editor Script Plugin** in your project if needed. The script targets Unreal Engine **5.6.1** and its editor Python API; other versions may require adjustments.
2. Keep [`asset_auditor.py`](Scripts/asset_auditor.py) and [`dashboard_template.html`](Scripts/dashboard_template.html) together in `Scripts/`.
3. Open the level you want to inspect and choose **Tools → Execute Python Script…**, then select `asset_auditor.py`.
4. Open the generated HTML or JSON under the tool's `Reports/` folder. Files use incremental names such as `Audit_ProjectName_v00.json`.

The script loads asset objects during inspection; scanning a large content folder can take time and temporarily increase editor memory use. It does not modify asset settings.

By **Igor G. Streiff**, developed for the Max Sarlija Academy Tech Art course. [MIT License](LICENSE).

---

<a id="español"></a>
# UE Asset Auditor

**Inventario y revisión básica de assets para Unreal Engine.**

*[English above](#english)*

<div align="center">
  <img src="UE_AssetAuditor_banner.png" alt="UE Asset Auditor" width="100%">
</div>

Ejercicio de automatización en Python desarrollado durante el curso de Tech Art. Recopila información de assets y ciertas configuraciones del nivel, aplica reglas simples de revisión y exporta un dashboard HTML con buscador y un reporte JSON. Su propósito es facilitar una inspección inicial que se pueda compartir y revisar fuera del editor.

## Demostración

https://github.com/user-attachments/assets/c9fad7df-e1e5-41ee-956e-0126d166bbda

La grabación muestra el ejercicio original. El reporte actual presenta las alertas como observaciones para revisar y muestra **N/A** cuando una propiedad no está disponible.

## Qué Recopila

- **Static meshes:** vértices y triángulos de LOD 0, cantidad de LODs, estado de Nanite, slots de material y configuración de colisión.
- **Assets Texture2D:** dimensiones en píxeles.
- **Assets Material:** modo de mezcla. Las instancias de material quedan fuera de este escaneo.
- **Assets SoundWave:** configuración explícita de carga, cuando puede leerse.
- **Blueprints y Level Sequences:** nombres y rutas de paquete; solo inventario.
- **Actores cargados del nivel:** luces, estado unbounded de PostProcessVolume y configuración de niebla volumétrica de ExponentialHeightFog.
- **Referencias de paquetes:** assets sin referencias entrantes hard/soft detectadas por esta consulta.

Los assets se buscan dentro de **`/Game`**; el contenido del motor y los plugins queda fuera del alcance. La información de actores corresponde a lo cargado en el editor, no a todos los mapas ni a celdas descargadas de World Partition.

## Reglas de Revisión

Son indicaciones para investigar, no fallos de rendimiento medidos ni límites universales de producción.

| Tag | Condición registrada |
|-----|----------------------|
| `MESH_LOD` | Nanite desactivado y menos de 3 LODs |
| `MESH_HEAVY` | Más de 100.000 triángulos en LOD 0 |
| `MESH_SLOTS` | Más de 5 slots de material |
| `MESH_COLLISION` | Complex Collision as Simple configurado |
| `TEX_LARGE` | Alguna dimensión supera los 2048 px |
| `MAT_TRANSLUCENT` | Modo de mezcla translúcido |
| `FOG_VOLUMETRIC` | Niebla volumétrica activada |
| `AUDIO_INLINE` | Force Inline configurado explícitamente |
| `ORPHAN` | Sin referencias entrantes de paquetes detectadas; **no demuestra que el asset esté sin usar** |
| `READ_ERROR` | No se pudo inspeccionar una propiedad o asset; consultar el log de Unreal |

Los umbrales son valores predeterminados de los métodos Python, no presupuestos recomendados para cualquier asset o plataforma. La ausencia de referencias detectadas no recomienda borrar: mapas de entrada, cargas desde código/configuración y reglas del Asset Manager requieren una revisión aparte.

**Alcance:** este reporte no mide tiempo por cuadro, costo de CPU/GPU, memoria RAM/VRAM residente, presión de streaming ni capacidad de sostener tiempo real. El diagnóstico de rendimiento requiere mediciones durante la ejecución con las herramientas de profiling de Unreal. No se infiere la topología original de ngons a partir de conteos de triángulos/vértices.

Las lecturas fallidas se guardan como `null` en JSON y se muestran como **N/A**, distinguiéndolas de valores cero o falso comprobados. Si se cancela un escaneo o faltan datos, el reporte se marca **parcial**; los contadores corresponden a las entradas efectivamente registradas. Las Level Sequences figuran en JSON; el dashboard conserva sus pestañas existentes de assets y actores.

## Ejecutar en Unreal Editor

1. Activá **Python Editor Script Plugin** en el proyecto si hace falta. El script está orientado a Unreal Engine **5.6.1** y su API Python del editor; otras versiones pueden requerir ajustes.
2. Conservá juntos [`asset_auditor.py`](Scripts/asset_auditor.py) y [`dashboard_template.html`](Scripts/dashboard_template.html) dentro de `Scripts/`.
3. Abrí el nivel que querés inspeccionar y elegí **Tools → Execute Python Script…**. Seleccioná `asset_auditor.py`.
4. Abrí el HTML o JSON generado dentro de `Reports/` de la herramienta. Los nombres se incrementan, por ejemplo `Audit_ProjectName_v00.json`.

El script carga objetos de los assets durante la inspección; escanear mucho contenido puede tardar y aumentar temporalmente la memoria usada por el editor. No modifica configuraciones de los assets.

Por **Igor G. Streiff**, desarrollado para el curso de Tech Art de Max Sarlija Academy. [Licencia MIT](LICENSE).
