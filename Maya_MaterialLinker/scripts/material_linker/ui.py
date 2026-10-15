"""Small Maya window for matching PBR exports to existing Arnold materials."""
from __future__ import annotations

import json
import os
from pathlib import Path

import maya.cmds as cmds
from .core import MaterialLinker, MAP_SUFFIXES

_EXTENSIONS = ('.tif', '.tiff', '.png', '.exr')
_WINDOW = 'materialLinkerWindow'
_INSTANCE = None


class FolderLinker(MaterialLinker):
    """Use the artist's chosen folder without changing the Maya workspace."""
    def __init__(self, folder, config, dry_run=True):
        self.folder = os.path.normpath(folder)
        if not os.path.isdir(self.folder):
            raise ValueError('Choose an existing texture folder.')
        super().__init__(config_dict=config, dry_run=dry_run)

    def _resolve_sourceimages_dir(self):
        return self.folder


def _key(name):
    name = name.rsplit(':', 1)[-1]
    return ''.join(c.lower() for c in name if c.isalnum())


class MaterialLinkerWindow:
    def __init__(self):
        self.folder = ''
        self.rows = []
        self.catalog = {}
        self.preview_signature = None
        self.last_report = None
        self.defaults = {}
        preset = Path(__file__).resolve().parents[2] / 'material_link_map.json'
        try:
            self.defaults = json.loads(preset.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass

    def show(self):
        if cmds.window(_WINDOW, exists=True):
            cmds.deleteUI(_WINDOW)
        cmds.window(_WINDOW, title='Material Linker | Maya Arnold', widthHeight=(700, 630), sizeable=True)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=7, columnAttach=('both', 14))
        cmds.separator(height=3, style='none')
        cmds.text(label='Material Linker', align='left', font='boldLabelFont', height=24)
        cmds.text(label='Choose textures  >  Match materials  >  Preview  >  Connect', align='left')
        cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(88, 440, 112))
        cmds.text(label='Texture folder', align='left')
        self.folder_field = cmds.textField(editable=False, text='Choose a folder...')
        cmds.button(label='Browse...', command=self.browse, width=98)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(88, 440, 112))
        cmds.text(label='Asset prefix', align='left')
        self.prefix_menu = cmds.optionMenu(changeCommand=self.scan)
        cmds.menuItem(label='(Scan textures)')
        cmds.button(label='Scan / Refresh', command=self.scan, width=98)
        cmds.setParent('..')
        cmds.frameLayout(label='Materials in scene  /  Texture sets', collapsable=False, marginWidth=8, marginHeight=6)
        self.scroll = cmds.scrollLayout(height=125, childResizable=True)
        self.table = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        cmds.setParent('..')
        cmds.setParent('..')
        self.emission = cmds.checkBox(label='Include Emissive maps', value=False, changeCommand=self.invalidate)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnWidth2=(330, 330))
        self.preview_button = cmds.button(label='Preview', height=36, command=self.preview, backgroundColor=(0.24, 0.37, 0.46))
        self.connect_button = cmds.button(label='Connect textures', width=318, height=36, enable=False, command=self.connect,
                                         annotation='Preview the current mapping first.', backgroundColor=(0.27, 0.43, 0.32))
        cmds.setParent('..')
        self.status = cmds.text(label='Choose a texture folder, then scan your scene.', align='left', height=24)
        self.output = cmds.scrollField(editable=False, wordWrap=False, height=180, text='')
        cmds.text(label='BaseColor  /  Roughness  /  Metalness  /  Normal     |     Maya Undo supported', align='left', font='smallPlainLabelFont')
        cmds.separator(height=3, style='none')
        cmds.showWindow(_WINDOW)
        project = cmds.workspace(q=True, rootDirectory=True)
        rule = cmds.workspace(fileRuleEntry='sourceImages') or 'sourceimages'
        folder = os.path.normpath(os.path.join(project, rule))
        if os.path.isdir(folder):
            self.set_folder(folder)
        return self

    def set_folder(self, folder):
        self.folder = os.path.normpath(folder)
        path = Path(self.folder)
        display = f'{path.parent.name} / {path.name}'
        cmds.textField(self.folder_field, e=True, text=display, annotation=self.folder)
        self.scan()

    def browse(self, *_):
        paths = cmds.fileDialog2(fileMode=3, dialogStyle=2, caption='Choose texture folder', okCaption='Choose')
        if paths:
            self.set_folder(paths[0])

    def invalidate(self, *_):
        self.preview_signature = None
        cmds.button(self.connect_button, e=True, enable=False)
        cmds.scrollField(self.output, e=True, text='')
        cmds.text(self.status, e=True, label='Preview the current mapping before connecting.')

    def mappings(self):
        result = []
        for material, menu, tokens in self.rows:
            if not cmds.optionMenu(menu, exists=True):
                continue
            index = cmds.optionMenu(menu, q=True, select=True) - 1
            if index > 0:
                result.append({'maya_material': material, 'texture_token': tokens[index]})
        return result

    def config(self):
        prefix = cmds.optionMenu(self.prefix_menu, q=True, value=True)
        skipped = ['Height']
        if not cmds.checkBox(self.emission, q=True, value=True):
            skipped.append('Emissive')
        return {'texture_prefix': prefix, 'texture_extensions': list(_EXTENSIONS),
                'mappings': self.mappings(), 'skip_maps': skipped}

    def scan(self, *_):
        previous = {m['maya_material']: m['texture_token'] for m in self.mappings()}
        old_prefix = cmds.optionMenu(self.prefix_menu, q=True, value=True)
        self.invalidate()
        self.rows = []
        children = cmds.columnLayout(self.table, q=True, childArray=True) or []
        for child in children:
            cmds.deleteUI(child)
        if not self.folder or not os.path.isdir(self.folder):
            cmds.text(self.status, e=True, label='Choose an existing texture folder.')
            return
        try:
            if not cmds.pluginInfo('mtoa', q=True, loaded=True):
                cmds.loadPlugin('mtoa', quiet=True)
            filenames = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
            prefixes = sorted({os.path.splitext(f)[0].split('_M_', 1)[0] for f in filenames
                               if os.path.splitext(f)[1].lower() in _EXTENSIONS and '_M_' in f
                               and os.path.splitext(f)[0].endswith(tuple('_'+s for s in MAP_SUFFIXES))})
            for item in cmds.optionMenu(self.prefix_menu, q=True, itemListLong=True) or []:
                cmds.deleteUI(item)
            for prefix in prefixes or ['(No matching exports)']:
                cmds.menuItem(parent=self.prefix_menu, label=prefix)
            if old_prefix in prefixes:
                cmds.optionMenu(self.prefix_menu, e=True, value=old_prefix)
            if not prefixes:
                cmds.text(self.status, e=True, label='No matching exports. Expected: Asset_M_TextureSet_BaseColor.png')
                return
            config = self.config()
            linker = FolderLinker(self.folder, config, dry_run=True)
            self.catalog = linker.textures
            tokens = sorted(self.catalog)
            materials = sorted(cmds.ls(type='aiStandardSurface') or [])
            aliases = {}
            if config['texture_prefix'] == self.defaults.get('texture_prefix'):
                aliases = {m['maya_material']: m['texture_token'] for m in self.defaults.get('mappings', [])}
            for material in materials:
                row = cmds.rowLayout(parent=self.table, numberOfColumns=2, adjustableColumn=2, columnWidth2=(285, 300))
                cmds.text(label=material, align='left', parent=row)
                menu = cmds.optionMenu(parent=row, changeCommand=self.invalidate)
                values = [None] + tokens
                cmds.menuItem(label='(Skip this material)', parent=menu)
                for token in tokens:
                    cmds.menuItem(label=f'{token}  ({len(self.catalog[token])} maps)', parent=menu)
                short = material.rsplit(':', 1)[-1]
                name_token = short[2:] if short.startswith('M_') else short
                exact = next((t for t in tokens if _key(t) == _key(name_token)), None)
                chosen = previous.get(material) or exact or aliases.get(material)
                if chosen in tokens:
                    cmds.optionMenu(menu, e=True, select=values.index(chosen)+1)
                self.rows.append((material, menu, values))
            if not materials:
                cmds.text(parent=self.table, label='Open a scene with Arnold materials, then Scan / Refresh.', align='left')
            cmds.text(self.status, e=True, label=f'{len(tokens)} texture sets found  |  {len(materials)} Arnold materials in scene')
        except Exception as exc:
            cmds.text(self.status, e=True, label='Could not scan. See the message below.')
            cmds.scrollField(self.output, e=True, text=str(exc))

    def signature(self, config):
        files = [(entry.name, entry.stat().st_size, entry.stat().st_mtime_ns)
                 for entry in os.scandir(self.folder) if entry.is_file() and entry.name.lower().endswith(_EXTENSIONS)]
        scene = []
        for mapping in config['mappings']:
            mat = mapping['maya_material']
            scene.append((mat, cmds.ls(mat, uuid=True),
                          sorted(cmds.listConnections(mat, s=True, d=False, plugs=True, connections=True) or [])))
        textures = [(n, cmds.getAttr(n+'.fileTextureName'), cmds.getAttr(n+'.colorSpace')) for n in cmds.ls(type='file') or []]
        return json.dumps([self.folder, config, sorted(files), scene, sorted(textures)], sort_keys=True)

    def write_report(self, report, dry_run):
        action = 'PREVIEW - scene unchanged' if dry_run else 'CONNECTED'
        count = len(report['linked'])
        existing = len(report['skipped_existing'])
        lines = [action, f'{count} connections '+('planned' if dry_run else 'made')+f' | {existing} already correct', '']
        sections = [('Planned links' if dry_run else 'Linked textures', 'linked'),
                    ('Already correct', 'skipped_existing'), ('Missing maps', 'missing_maps'),
                    ('Missing materials', 'missing_materials'), ('Errors', 'errors'), ('Warnings', 'warnings')]
        for title, key in sections:
            items = report.get(key) or []
            if key == 'warnings':
                items = [item for item in items if 'listed in skip_maps' not in item]
            if items:
                lines.extend([title+':'] + ['  '+str(item) for item in items] + [''])
        cmds.scrollField(self.output, e=True, text='\n'.join(lines))
        problems = len(report['errors'])+len(report['missing_maps'])+len(report['missing_materials'])
        label = (f'Preview: {count} connections ready' if dry_run else f'Connected {count} texture maps')
        if problems:
            label = f'{problems} issue(s) to review - see report'
        elif not count and existing:
            label = f'All {existing} connections are already correct'
        cmds.text(self.status, e=True, label=label)
        return not problems and bool(count)

    def preview(self, *_):
        self.last_report = None
        self.preview_signature = None
        cmds.button(self.connect_button, e=True, enable=False)
        try:
            config = self.config()
            if not config['mappings']:
                raise ValueError('Choose a texture set for at least one material.')
            self.last_report = FolderLinker(self.folder, config, dry_run=True).run()
            valid = self.write_report(self.last_report, True)
            if valid:
                self.preview_signature = self.signature(config)
                cmds.button(self.connect_button, e=True, enable=True)
        except Exception as exc:
            cmds.text(self.status, e=True, label='Preview could not complete.')
            cmds.scrollField(self.output, e=True, text=str(exc))
        return self.last_report

    def connect(self, *_):
        try:
            config = self.config()
            if not self.preview_signature or self.signature(config) != self.preview_signature:
                self.invalidate()
                cmds.text(self.status, e=True, label='Inputs or scene changed. Preview again before connecting.')
                return None
            cmds.undoInfo(openChunk=True, chunkName='Material Linker')
            try:
                self.last_report = FolderLinker(self.folder, config, dry_run=False).run()
            finally:
                cmds.undoInfo(closeChunk=True)
            self.write_report(self.last_report, False)
            return self.last_report
        except Exception as exc:
            cmds.text(self.status, e=True, label='Connection failed. Maya Undo is available for applied changes.')
            cmds.scrollField(self.output, e=True, text=str(exc))
        finally:
            self.preview_signature = None
            cmds.button(self.connect_button, e=True, enable=False)


def show():
    """Show one Material Linker window in Maya."""
    global _INSTANCE
    _INSTANCE = MaterialLinkerWindow().show()
    return _INSTANCE
