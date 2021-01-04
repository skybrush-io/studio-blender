from .base import LightEffectOperator

__all__ = ("CreateLightEffectOperator",)


class CreateLightEffectOperator(LightEffectOperator):
    """Blender operator that creates a new light effect."""

    bl_idname = "skybrush.create_light_effect"
    bl_label = "Create Light Effect"
    bl_description = "Creates a new light effect at the end of the effect list."

    def execute_on_light_effect_collection(self, light_effects, context):
        light_effects.append_new_entry(name="Untitled", select=True)
        return {"FINISHED"}
