import os
from json import load

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from sbstudio.plugin.model.light_effects import LightEffectCollection
from sbstudio.plugin.props.light_effects import LightEffectSelectionProperty

from .base import LightEffectOperator

__all__ = ("ImportLightEffectsOperator",)


class ImportLightEffectsOperator(LightEffectOperator, ImportHelper):
    """Blender operator that imports one or more light effects."""

    bl_idname = "skybrush.import_light_effects"
    bl_label = "Import Light Effects"
    bl_description = "Imports one or more light effects into the light effect list"

    filter_glob = StringProperty(default="*.json", options={"HIDDEN"})
    filename_ext = ".json"

    selection = LightEffectSelectionProperty(add_selected=False)

    def execute_on_light_effect_collection(
        self, light_effects: LightEffectCollection, context
    ):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        warnings: list[str] = []

        if os.path.basename(filepath).lower() == self.filename_ext.lower():
            self.report({"ERROR_INVALID_INPUT"}, "Filename must not be empty")
            return {"CANCELLED"}

        with open(filepath, "r") as fp:
            data = load(fp)

        for name, entry in data.items():
            if self.selection == "ENABLED" and not entry.get("enabled"):
                continue
            # TODO: make name unique
            light_effect = light_effects.append_new_entry(name)
            warnings.extend(light_effect.update_from_dict(entry))

        if warnings:
            if len(warnings) > 1:
                more = len(warnings) - 1
                self.report({"WARNING"}, warnings[0] + f" (+{more} more warning(s))")
            else:
                self.report({"WARNING"}, warnings[0])
        else:
            self.report({"INFO"}, f"Imported {len(data)} light effects successfully")

        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}{self.filename_ext}"

        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
