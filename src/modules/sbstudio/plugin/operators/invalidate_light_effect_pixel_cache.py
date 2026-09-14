from bpy.types import Context

from sbstudio.plugin.model.light_effects import (
    LightEffectCollection,
)
from sbstudio.plugin.tasks.light_effects import update_light_effects
from sbstudio.plugin.views import redraw_all_3d_views

from .base import LightEffectOperator

__all__ = ("InvalidateLightEffectPixelCacheOperator",)


class InvalidateLightEffectPixelCacheOperator(LightEffectOperator):
    """Blender operator that invalidates the cached pixel-level representation
    of the image associated to the selected light effect.
    """

    bl_idname = "skybrush.invalidate_light_effect_pixel_cache"
    bl_label = "Refresh Light Effect Image"
    bl_description = (
        "Refreshes the image associated to the light effect when the image changes"
    )

    @classmethod
    def poll(cls, context: Context):
        return (
            LightEffectOperator.poll(context)
            and context.scene.skybrush.light_effects.active_entry is not None
        )

    def execute_on_light_effect_collection(
        self, light_effects: LightEffectCollection, context: Context
    ):
        entry = light_effects.active_entry
        assert entry is not None

        entry.invalidate_color_image()

        # apparently these are necessary when switching from a static image to a
        # dynamic one, otherwise the image is not updated in the 3D view
        update_light_effects(context.scene, context.evaluated_depsgraph_get())
        redraw_all_3d_views()

        return {"FINISHED"}
