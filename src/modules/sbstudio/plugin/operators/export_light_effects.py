import bpy
import os

from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from json import dump

from sbstudio.plugin.model.light_effects import LightEffectCollection

from .base import LightEffectOperator


__all__ = ("ExportLightEffectsOperator",)


class ExportLightEffectsOperator(LightEffectOperator, ExportHelper):
    """Blender operator that exports one or more light effects."""

    bl_idname = "skybrush.export_light_effects"
    bl_label = "Export Light Effects"
    bl_description = "Exports one or more light effects from the light effect list"

    filter_glob = StringProperty(default="*.json", options={"HIDDEN"})
    filename_ext = ".json"

    # whether to export all light effects or only enabled ones
    export_enabled_only = BoolProperty(
        name="Export enabled only",
        default=False,
        description=(
            "Export only the enabled light effects. "
            "Uncheck to export all light effects, irrespectively of their enabled state."
        ),
    )

    def execute_on_light_effect_collection(
        self, light_effects: LightEffectCollection, context
    ):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)

        if os.path.basename(filepath).lower() == self.filename_ext.lower():
            self.report({"ERROR_INVALID_INPUT"}, "Filename must not be empty")
            return {"CANCELLED"}

        # TODO: make sure light effect names are unique
        data = {
            light_effect.name: light_effect.as_dict()
            for light_effect in light_effects.entries
            if (not self.export_enabled_only or light_effect.enabled)
        }

        with open(filepath, "w") as fp:
            dump(data, fp, indent=2)

        self.report({"INFO"}, f"Exported {len(data)} light effects successfully")

        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}{self.filename_ext}"

        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
