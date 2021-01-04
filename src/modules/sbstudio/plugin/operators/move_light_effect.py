from .base import LightEffectOperator

__all__ = ("MoveLightEffectDownOperator", "MoveLightEffectUpOperator")


class MoveLightEffectDownOperator(LightEffectOperator):
    """Blender operator that moves the selected light effect one slot down
    in the light effect list.
    """

    bl_idname = "skybrush.move_light_effect_down"
    bl_label = "Move Selected Light Effect Down"
    bl_description = (
        "Moves the selected light effect down by one slot in the light effect list"
    )

    @classmethod
    def poll(cls, context):
        if not LightEffectOperator.poll(context):
            return False

        light_effects = context.scene.skybrush.light_effects
        if light_effects.active_entry is None:
            return False

        return (
            light_effects.active_entry is not None
            and light_effects.active_entry_index < len(light_effects.entries) - 1
        )

    def execute_on_light_effect_collection(self, light_effects, context):
        light_effects.move_active_entry_down()
        return {"FINISHED"}


class MoveLightEffectUpOperator(LightEffectOperator):
    """Blender operator that moves the selected light effect one slot up
    in the light effect list.
    """

    bl_idname = "skybrush.move_light_effect_up"
    bl_label = "Move Selected Light Effect Up"
    bl_description = (
        "Moves the selected light effect up by one slot in the light effect list"
    )

    @classmethod
    def poll(cls, context):
        if not LightEffectOperator.poll(context):
            return False

        light_effects = context.scene.skybrush.light_effects
        if light_effects.active_entry is None:
            return False

        return (
            light_effects.active_entry is not None
            and light_effects.active_entry_index > 0
        )

    def execute_on_light_effect_collection(self, light_effects, context):
        light_effects.move_active_entry_up()
        return {"FINISHED"}
