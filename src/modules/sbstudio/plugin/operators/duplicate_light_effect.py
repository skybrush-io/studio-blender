from .base import LightEffectOperator

__all__ = ("DuplicateLightEffectOperator",)


class DuplicateLightEffectOperator(LightEffectOperator):
    """Blender operator that duplicates the currently selected new light effect."""

    bl_idname = "skybrush.duplicate_light_effect"
    bl_label = "Duplicate Light Effect"
    bl_description = "Duplicates the selected light effect in the effect list"

    @classmethod
    def poll(cls, context):
        return (
            LightEffectOperator.poll(context)
            and context.scene.skybrush.light_effects.active_entry is not None
        )

    def execute_on_light_effect_collection(self, light_effects, context):
        light_effects.duplicate_selected_entry(select=True, context=context)
        return {"FINISHED"}
