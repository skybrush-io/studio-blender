from .base import LightEffectOperator

__all__ = (
    "SetLightEffectEndFrameOperator",
    "SetLightEffectStartFrameOperator",
)


class SetLightEffectEndFrameOperator(LightEffectOperator):
    """Blender operator that sets the end frame of the active light effect
    to the current frame."""

    bl_idname = "skybrush.set_light_effect_end_frame"
    bl_label = "Set Light Effect End Frame"
    bl_description = "Sets the end frame of the light effect to the current frame."

    def execute_on_light_effect_collection(self, light_effects, context):
        light_effect = light_effects.active_entry
        if light_effect is not None:
            light_effect.frame_end = context.scene.frame_current
        return {"FINISHED"}


class SetLightEffectStartFrameOperator(LightEffectOperator):
    """Blender operator that sets the start frame of the active light effect
    to the current frame."""

    bl_idname = "skybrush.set_light_effect_start_frame"
    bl_label = "Set Light Effect Start Frame"
    bl_description = "Sets the start frame of the light effect to the current frame."

    def execute_on_light_effect_collection(self, light_effects, context):
        light_effect = light_effects.active_entry
        if light_effect is not None:
            light_effect.frame_start = context.scene.frame_current
        return {"FINISHED"}
