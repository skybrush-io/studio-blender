from bpy.types import Panel

from sbstudio.plugin.operators import ValidateTrajectoriesOperator

__all__ = ("SafetyCheckPanel",)


class SafetyCheckPanel(Panel):
    """Custom Blender panel that allows the user to set the parameters of the
    flight safety checks and to inspect the minimum distance and maximum
    velocity of the drones in the current Blender frame.
    """

    bl_idname = "OBJECT_PT_skybrush_safety_check_panel"
    bl_label = "Safety Check"

    # The following three settings determine that the LED control panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Safety & Export"

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush.safety_check

    def draw(self, context):
        scene = context.scene
        safety_check = scene.skybrush.safety_check
        settings = scene.skybrush.settings

        if not safety_check or not settings:
            return

        layout = self.layout

        layout.prop(safety_check, "enabled")
        layout.separator()

        row = layout.row()
        row.enabled = safety_check.enabled

        col = row.column()
        col.prop(safety_check, "proximity_warning_enabled")
        row = col.row()
        row.prop(
            safety_check,
            "proximity_warning_threshold",
            text="",
        )
        row.enabled = safety_check.proximity_warning_enabled

        col.prop(safety_check, "altitude_warning_enabled")
        row = col.row()
        row.prop(
            safety_check,
            "altitude_warning_threshold",
            text="",
        )
        row.enabled = safety_check.altitude_warning_enabled

        col.prop(safety_check, "velocity_warning_enabled")
        row = col.row()
        row.prop(
            safety_check,
            "velocity_xy_warning_threshold",
            text="XY",
        )
        row.prop(
            safety_check,
            "velocity_z_warning_threshold",
            text="Z",
        )
        row.enabled = safety_check.velocity_warning_enabled

        layout.separator()

        layout.operator(ValidateTrajectoriesOperator.bl_idname)
