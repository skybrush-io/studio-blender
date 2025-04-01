from bpy.types import Panel

__all__ = ("ShowPanel",)


class ShowPanel(Panel):
    """Custom Blender panel that allows the user to specify the properties of
    the show, inclusing its type, location and orientation.
    """

    bl_idname = "OBJECT_PT_skybrush_show_panel"
    bl_label = "Show"

    # The following three settings determine that the show control panel gets
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

        layout.prop(settings, "show_type", text="Type")
        layout.prop(
            settings, "use_show_origin_and_orientation", text="Specify location"
        )

        col = layout.column()
        col.prop(settings, "latitude_of_show_origin", text="Latitude")
        col.prop(settings, "longitude_of_show_origin", text="Longitude")
        col.prop(settings, "show_orientation", text="X+ axis orientation")
        col.enabled = settings.use_show_origin_and_orientation
