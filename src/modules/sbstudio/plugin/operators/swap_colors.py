from bpy.types import Operator

__all__ = ("SwapColorsInLEDControlPanelOperator",)


class SwapColorsInLEDControlPanelOperator(Operator):
    """Swaps the current primary and secondary colors in the LED control panel."""

    bl_idname = "skybrush.swap_colors_in_led_control_panel"
    bl_label = "Swap Colors in LED Control Panel"
    bl_description = (
        "Swaps the current primary and secondary colors in the LED control panel."
    )

    def execute(self, context):
        led_control = context.scene.skybrush.led_control
        led_control.swap_colors()
        return {"FINISHED"}
