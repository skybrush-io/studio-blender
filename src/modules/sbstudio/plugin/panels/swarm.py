from bpy.types import Panel

from sbstudio.plugin.constants import Collections

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
    bl_category = "Skybrush"

    def draw(self, context):
        scene = context.scene
        settings = scene.skybrush.settings

        if not settings:
            return

        layout = self.layout

        layout.prop(settings, "drone_collection", text="Drones")
        layout.prop(settings, "max_acceleration", slider=True)

        if Collections.find_templates(create=False) is None:
            layout.prop(settings, "drone_template", text="Drone")
            row = layout.row(heading="Drone radius")
            row.prop(settings, "drone_radius", text="")
            if settings.drone_template not in ["SPHERE", "CONE"]:
                row.enabled = False

            layout.separator()
