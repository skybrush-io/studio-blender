from bpy.types import Panel

from sbstudio.plugin.constants import Collections

from sbstudio.plugin.operators import (
    CreateTakeoffGridOperator,
    LandOperator,
    ReturnToHomeOperator,
    TakeoffOperator,
)

__all__ = ("SwarmPanel",)


class SwarmPanel(Panel):
    """Custom Blender panel that allows the user to create a drone swarm and
    to perform mass-takeoff and mass-landing operations on it.
    """

    bl_idname = "OBJECT_PT_skybrush_swarm_panel"
    bl_label = "Swarm"

    # The following three settings determine that the swarm control panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Formations"

    def draw(self, context):
        scene = context.scene
        settings = scene.skybrush.settings

        if not settings:
            return

        layout = self.layout

        layout.prop(settings, "show_type", text="Show")
        layout.prop(settings, "drone_collection", text="Drones")
        layout.prop(settings, "max_acceleration", slider=True)

        layout.separator()

        if Collections.find_templates(create=False) is None:
            layout.prop(settings, "drone_template", text="Drone")
            row = layout.row(heading="Drone radius")
            row.prop(settings, "drone_radius", text="")
            if settings.drone_template not in ["SPHERE", "CONE"]:
                row.enabled = False

            layout.separator()

        layout.operator(CreateTakeoffGridOperator.bl_idname, icon="ADD")

        row = layout.row(align=True)
        row.operator(TakeoffOperator.bl_idname, text="Takeoff", icon="TRIA_UP_BAR")
        row.operator(ReturnToHomeOperator.bl_idname, text="RTH", icon="HOME")
        row.operator(LandOperator.bl_idname, text="Land", icon="TRIA_DOWN_BAR")
