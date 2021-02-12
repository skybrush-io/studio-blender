from bpy.types import Panel

from sbstudio.plugin.operators import (
    CreateTakeoffGridOperator,
    LandOperator,
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

        layout.prop(settings, "drone_collection", text="Drones")

        layout.prop(settings, "max_acceleration", slider=True)

        layout.separator()

        layout.operator(CreateTakeoffGridOperator.bl_idname, icon="ADD")

        row = layout.row()
        row.operator(TakeoffOperator.bl_idname, text="Takeoff", icon="TRIA_UP_BAR")
        row.operator(LandOperator.bl_idname, text="Land", icon="TRIA_DOWN_BAR")
