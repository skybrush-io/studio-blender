from bpy.types import Panel

from sbstudio.plugin.operators import CreateTakeoffGridOperator

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

        layout.prop(settings, "max_acceleration", slider=True)

        layout.separator()

        layout.operator(CreateTakeoffGridOperator.bl_idname, icon="ADD")
