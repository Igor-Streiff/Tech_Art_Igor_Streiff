[MatLink](../README.es.md) · [English](USAGE.md)

# Instalación y uso

## Requisitos

Maya con Arnold / MtoA y Python 3.10+. Los materiales deben existir como nodos `aiStandardSurface`. No requiere paquetes Python adicionales. La versión probada es Maya 2027.

## Abrir la herramienta

1. Descargá o cloná este repositorio y conservá completa la carpeta `Maya_MaterialLinker/`.
2. Abrí Maya y arrastrá [`open_material_linker.py`](../open_material_linker.py) al viewport.

También podés abrir ese archivo desde **Script Editor → File → Open Script** y ejecutarlo en una pestaña **Python**. Si solicita la carpeta, seleccioná `Maya_MaterialLinker/`.

## Preparar las texturas

Usá el formato `{prefijo}_M_{textureSet}_{mapa}.ext`:

```text
Asset_Rusty2_M_Madera_Organico_BaseColor.tif
Asset_Rusty2_M_Madera_Organico_Roughness.tif
Asset_Rusty2_M_Madera_Organico_Metalness.tif
Asset_Rusty2_M_Madera_Organico_Normal.tif
```

Extensiones admitidas: `.tif`, `.tiff`, `.png`, `.exr`.

| Sufijo del mapa | Entrada de Arnold | Color space |
| --- | --- | --- |
| `BaseColor` | `baseColor` | sRGB |
| `Roughness` | `specularRoughness` | Raw |
| `Metalness` | `metalness` | Raw |
| `Normal` | `aiNormalMap` → `normalCamera` | Raw |
| `Emissive` | `emissionColor` | sRGB |

Activá **Include Emissive maps** para conectar emisión. La ventana omite los mapas Height.

## Conectar un lote

1. Abrí la escena que contiene los materiales Arnold.
2. Elegí la carpeta de texturas con **Browse…**. Si existe `sourceimages/` en el proyecto activo, se escanea automáticamente. Elegir otra carpeta no cambia el proyecto de Maya.
3. Seleccioná **Asset prefix**. Para cada material, elegí su texture set o **Skip this material**. Los nombres coincidentes se seleccionan automáticamente; los demás se pueden asociar manualmente.
4. Presioná **Preview**. Revisá las conexiones previstas y resolvé los mapas faltantes, materiales ausentes o errores.
5. Presioná **Connect textures**. Un **Undo** de Maya revierte el lote aplicado.

Usá **Scan / Refresh** si agregás materiales o cambiás las texturas exportadas.

## Interpretar el resultado

- **Connect textures deshabilitado:** ejecutá Preview para la selección actual y resolvé los problemas indicados. Si hacés cambios después de Preview, necesitás otra revisión.
- **No matching exports:** revisá el formato de nombres, las extensiones y la carpeta elegida.
- **Un material no se asocia automáticamente:** elegí su texture set desde el selector. No es necesario que el material y la exportación tengan nombres idénticos.
- **Already correct:** el mapa ya está conectado a la entrada prevista; MatLink omite esa conexión en lugar de crear otro nodo.
- **Connection failed:** revisá el error en el reporte. Maya Undo sigue disponible para los cambios que llegaron a aplicarse.

## Flujo Python

El motor también acepta asociaciones mediante JSON. [`material_link_map.json`](../material_link_map.json) contiene un preset de Rusty; [`config_schema.json`](../scripts/material_linker/config_schema.json) describe los campos y las conexiones.

[`examples/load_in_maya.py`](../examples/load_in_maya.py) explica cómo cargar el paquete desde `scripts/` en un proyecto de Maya, con el config en la raíz y los mapas en `sourceimages/`.

```python
import run_linker

run_linker.run(config_path, dry_run=True)   # Revisar
run_linker.run(config_path, dry_run=False)  # Aplicar
```

[`validate_textures.py`](../scripts/material_linker/validate_textures.py) comprueba nombres de archivos fuera de Maya. No inspecciona conexiones de la escena.
