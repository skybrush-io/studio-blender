from sbstudio.plugin.model.light_effects import (
    invalidate_pixel_cache as invalidate_light_effect_pixel_cache,
)
from sbstudio.plugin.tasks.light_effects import update_light_effects
from sbstudio.plugin.views import find_all_3d_views_and_their_areas

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
        update_light_effects(context.scene, context.evaluated_depsgraph_get())

        # Mark all the 3D views to be redrawn
        for _, area in find_all_3d_views_and_their_areas():
            area.tag_redraw()

        return {"FINISHED"}
