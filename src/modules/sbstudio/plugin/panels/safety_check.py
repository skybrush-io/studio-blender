from bpy.types import Panel


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
    bl_category = "Skybrush"

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush.safety_check

    def draw(self, context):
        scene = context.scene
        safety_check = scene.skybrush.safety_check
        if not safety_check:
            return

        layout = self.layout

        row = layout.row()
        if safety_check.min_distance >= 0:
            row.label(text=f"Min distance: {safety_check.min_distance:.1f} m")
        else:
            row.label(text=f"Min distance: ---")
