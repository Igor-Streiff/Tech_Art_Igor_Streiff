"""Helper genérico de escenas de prueba — reutilizable para cualquier rig.

No tiene datos de ningún personaje: recibe todo por parámetro vía `RigDemoKit`.
Los personajes concretos se definen en `maya_kit/kits.py`.

La carpeta de escenas de cada kit se indica por `scenes_dir_rel`, relativa a la
raíz de la tool. Puede apuntar fuera de la tool (con `..`) para que la escena
viva en tu carpeta de práctica y la tool siga siendo portable/publicable.

Flujo por rig:
  <scenes_dir>/<clean>        copia limpia (no se modifica al ensuciar)
  <scenes_dir>/<messy>        misma escena con nombres sucios para probar

`maya.cmds` se importa de forma perezosa para que este módulo (y el registro
de kits) se pueda importar fuera de Maya sin fallar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_WINDOW = "rigRenamerWin"


def _cmds():
    import maya.cmds as cmds_module

    return cmds_module


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class RigDemoKit:
    """Config de un rig de prueba local. Sin lógica hardcodeada al personaje."""

    character: str
    top_group: str
    scenes_dir_rel: str
    clean_filename: str
    messy_filename: str
    messy_map: dict[str, str] = field(default_factory=dict)

    def scenes_dir(self) -> Path:
        return (_project_root() / self.scenes_dir_rel).resolve()

    def clean_scene_path(self) -> Path:
        return self.scenes_dir() / self.clean_filename

    def messy_scene_path(self) -> Path:
        return self.scenes_dir() / self.messy_filename

    def _require_clean_scene(self) -> Path:
        path = self.clean_scene_path()
        if not path.exists():
            raise FileNotFoundError(
                f"No hay copia local del rig en:\n  {path}\n"
                f"Copiá '{self.clean_filename}' ahí (una sola vez) desde tu original."
            )
        return path

    def open_clean_scene(self) -> str:
        cmds = _cmds()
        path = self._require_clean_scene()
        cmds.file(path.as_posix(), open=True, force=True)
        print(f"[rig_renamer] Escena limpia: {path}")
        return self.top_group

    def apply_messy_names(self) -> tuple[int, list[str]]:
        """Renombra controles a nombres sucios en la escena actual."""
        cmds = _cmds()
        renamed = 0
        missing: list[str] = []
        for old_name, messy_name in self.messy_map.items():
            if not cmds.objExists(old_name):
                missing.append(old_name)
                continue
            cmds.rename(old_name, messy_name)
            renamed += 1
        return renamed, missing

    def save_messy_scene(self) -> Path:
        cmds = _cmds()
        path = self.messy_scene_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        cmds.file(rename=path.as_posix())
        cmds.file(save=True, type="mayaAscii", force=True)
        print(f"[rig_renamer] Escena messy guardada: {path}")
        return path

    def fill_ui_fields(self) -> None:
        cmds = _cmds()
        if cmds.window(_WINDOW, exists=True):
            cmds.textField(_WINDOW + "_rig", edit=True, text=self.top_group)
            cmds.textField(_WINDOW + "_char", edit=True, text=self.character)

    def build_messy_scene_from_clean(self, open_ui_after: bool = False) -> str:
        """Limpia → ensucia nombres → guarda escena messy."""
        self.open_clean_scene()
        renamed, missing = self.apply_messy_names()
        self.save_messy_scene()
        print(f"[rig_renamer] Controles renombrados: {renamed}")
        if missing:
            print(f"[rig_renamer] No encontrados: {', '.join(missing)}")
        print(f"[rig_renamer] Top-group: {self.top_group} | personaje: {self.character}")

        if open_ui_after:
            self._open_ui_and_fill()
        return self.top_group

    def open_messy_scene(self, open_ui_after: bool = False) -> str:
        """Abre la escena messy ya generada (o la crea desde la limpia)."""
        cmds = _cmds()
        messy = self.messy_scene_path()
        if not messy.exists():
            print("[rig_renamer] No hay messy local; generando desde copia limpia…")
            return self.build_messy_scene_from_clean(open_ui_after=open_ui_after)

        cmds.file(messy.as_posix(), open=True, force=True)
        print(f"[rig_renamer] Escena messy: {messy}")
        if open_ui_after:
            self._open_ui_and_fill()
        return self.top_group

    def _open_ui_and_fill(self) -> None:
        from rig_renamer.maya_ui import show

        show()
        self.fill_ui_fields()
