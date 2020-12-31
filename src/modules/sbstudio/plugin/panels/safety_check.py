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

        layout.label(text="Current frame")

        col = layout.column()
        col.alert = safety_check.should_show_proximity_warning
        col.prop(safety_check, "min_distance")
        col.alert = False

        col = layout.column()
        col.alert = safety_check.should_show_altitude_warning
        col.prop(safety_check, "max_altitude")
        col.alert = False

        col = layout.column()
        col.alert = safety_check.should_show_velocity_xy_warning
        col.enabled = safety_check.max_velocities_are_valid
        col.prop(safety_check, "max_velocity_xy")
        col.alert = False

        col = layout.column()
        col.alert = safety_check.should_show_velocity_z_warning
        col.enabled = safety_check.max_velocities_are_valid
        col.prop(safety_check, "max_velocity_z")
        col.alert = False

        col = layout.column()
        col.separator()

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

        col.separator()

        col.operator(ValidateTrajectoriesOperator.bl_idname)
