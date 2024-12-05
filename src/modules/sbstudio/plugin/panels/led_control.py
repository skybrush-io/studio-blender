from bpy.types import Panel

from sbstudio.plugin.operators import (
    ApplyColorsToSelectedDronesOperator as ApplyColors,
)
from sbstudio.plugin.utils.bloom import bloom_effect_supported


class LEDControlPanel(Panel):
    """Custom Blender panel that allows the user to control the color of the
    LED lights of the drones in the current drone show.
    """

    bl_idname = "OBJECT_PT_skybrush_led_control_panel"
    bl_label = "LED Control"

    # The following three settings determine that the LED control panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LEDs"

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush.led_control

    def draw(self, context):
        scene = context.scene
        led_control = scene.skybrush.led_control
        if not led_control:
            return

        layout = self.layout

        row = layout.row()
        col = row.column()
        col.prop(led_control, "primary_color", text="Primary", icon="COLOR")
        col = row.column()
        col.operator(
            "skybrush.swap_colors_in_led_control_panel", icon="ARROW_LEFTRIGHT", text=""
        )
        col = row.column()
        col.prop(led_control, "secondary_color", text="Secondary", icon="COLOR")

        row = layout.row()
        params = row.operator(ApplyColors.bl_idname, text="Apply")
        params.color = "PRIMARY"
        params.fade = False
        params = row.operator(ApplyColors.bl_idname, text="Apply")
        params.color = "SECONDARY"
        params.fade = False

        row = layout.row()
        params = row.operator(ApplyColors.bl_idname, text="Fade to")
        params.color = "PRIMARY"
        params.fade = True
        params = row.operator(ApplyColors.bl_idname, text="Fade to")
        params.color = "SECONDARY"
        params.fade = True

        if bloom_effect_supported():
            layout.separator()

            row = layout.row()
            row.prop(scene.skybrush.settings, "use_bloom_effect")
            row.prop(scene.skybrush.settings, "emission_strength")
