import bpy
import os

from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from json import load

from sbstudio.plugin.model.light_effects import LightEffectCollection

from .base import LightEffectOperator


__all__ = ("ImportLightEffectsOperator",)


class ImportLightEffectsOperator(LightEffectOperator, ImportHelper):
    """Blender operator that imports one or more light effects."""

    bl_idname = "skybrush.import_light_effects"
    bl_label = "Import Light Effects"
    bl_description = "Imports one or more light effects into the light effect list"

    filter_glob = StringProperty(default="*.json", options={"HIDDEN"})
    filename_ext = ".json"

    # whether to import all light effects or only enabled ones
    import_enabled_only = BoolProperty(
        name="Import enabled only",
        default=False,
        description=(
            "Import only the enabled light effects. "
            "Uncheck to import all light effects, irrespectively of their enabled state."
        ),
    )

    def execute_on_light_effect_collection(
        self, light_effects: LightEffectCollection, context
    ):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)

        if os.path.basename(filepath).lower() == self.filename_ext.lower():
            self.report({"ERROR_INVALID_INPUT"}, "Filename must not be empty")
            return {"CANCELLED"}

        with open(filepath, "r") as fp:
            data = load(fp)

        for name, entry in data.items():
            if self.import_enabled_only and not entry.get("enabled"):
                continue
            # TODO: make name unique
            light_effect = light_effects.append_new_entry(name)
            light_effect.update_from_dict(entry)

        self.report({"INFO"}, f"Imported {len(data)} light effects successfully")

        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}{self.filename_ext}"

        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
