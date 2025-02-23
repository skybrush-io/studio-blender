from sbstudio.plugin.model.light_effects import (
    invalidate_pixel_cache as invalidate_light_effect_pixel_cache,
)

from .base import LightEffectOperator

__all__ = ("RemoveLightEffectOperator",)


class RemoveLightEffectOperator(LightEffectOperator):
    """Blender operator that removes the selected light effect."""

    bl_idname = "skybrush.remove_light_effect"
    bl_label = "Remove Light Effect"
    bl_description = "Remove the selected light effect from the show"

    @classmethod
    def poll(cls, context):
        return (
            LightEffectOperator.poll(context)
            and context.scene.skybrush.light_effects.active_entry is not None
        )

    def execute_on_light_effect_collection(self, light_effects, context):
        light_effects.remove_active_entry()
        invalidate_light_effect_pixel_cache()
        return {"FINISHED"}
