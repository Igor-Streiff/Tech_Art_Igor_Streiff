[MatLink](../README.md) · [Español](USAGE.es.md)

# Installation and usage

## Requirements

Maya with Arnold / MtoA and Python 3.10+. The materials must already exist as `aiStandardSurface` nodes. No additional Python packages are required. Maya 2027 is the tested version.

## Open the tool

1. Download or clone this repository and keep the complete `Maya_MaterialLinker/` folder together.
2. Open Maya and drag [`open_material_linker.py`](../open_material_linker.py) into the viewport.

Alternatively, open that file through **Script Editor → File → Open Script** and execute it in a **Python** tab. If prompted, select the `Maya_MaterialLinker/` folder.

## Prepare texture exports

Use the filename pattern `{prefix}_M_{textureSet}_{map}.ext`:

```text
Asset_Rusty2_M_Madera_Organico_BaseColor.tif
Asset_Rusty2_M_Madera_Organico_Roughness.tif
Asset_Rusty2_M_Madera_Organico_Metalness.tif
Asset_Rusty2_M_Madera_Organico_Normal.tif
```

Supported extensions: `.tif`, `.tiff`, `.png`, `.exr`.

| Map suffix | Arnold input | Colour space |
| --- | --- | --- |
| `BaseColor` | `baseColor` | sRGB |
| `Roughness` | `specularRoughness` | Raw |
| `Metalness` | `metalness` | Raw |
| `Normal` | `aiNormalMap` → `normalCamera` | Raw |
| `Emissive` | `emissionColor` | sRGB |

Enable **Include Emissive maps** to connect emission. The window skips Height maps.

## Connect a batch

1. Open the scene containing your Arnold materials.
2. Choose the texture folder with **Browse…**. The active project's `sourceimages/` is scanned automatically when available. Choosing a different folder does not change the Maya project.
3. Select the **Asset prefix**. For each material, choose its texture set or **Skip this material**. Matching names are selected automatically; other names can be paired manually.
4. Click **Preview**. Review the planned links and resolve any missing maps, missing materials or errors.
5. Click **Connect textures**. One Maya **Undo** reverses the applied batch.

Use **Scan / Refresh** after adding materials or changing texture exports.

## Python workflow

The connection engine also accepts a JSON mapping. [`material_link_map.json`](../material_link_map.json) contains a Rusty preset; [`config_schema.json`](../scripts/material_linker/config_schema.json) describes the fields and bindings.

[`examples/load_in_maya.py`](../examples/load_in_maya.py) covers loading the package from a Maya project's `scripts/` folder, with the config at the project root and maps in `sourceimages/`.

```python
import run_linker

run_linker.run(config_path, dry_run=True)   # Review
run_linker.run(config_path, dry_run=False)  # Apply
```

[`validate_textures.py`](../scripts/material_linker/validate_textures.py) checks exported filenames outside Maya. It does not inspect scene connections.
