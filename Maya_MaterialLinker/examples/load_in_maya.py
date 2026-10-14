"""Preview Material Linker on the currently selected Maya project."""
import os
import sys
import maya.cmds as cmds

project_root = cmds.workspace(query=True, rootDirectory=True)
sys.path.insert(0, os.path.join(project_root, "scripts", "material_linker"))
import run_linker

config_path = os.path.join(project_root, "material_link_map.json")
report = run_linker.run(config_path, dry_run=True)

# After reviewing the report, apply from the Script Editor:
# report = run_linker.run(config_path, dry_run=False)
