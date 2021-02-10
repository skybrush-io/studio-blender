from bpy.types import Panel

from sbstudio.plugin.operators import UseSelectedVertexGroupForFormationOperator

__all__ = ("DroneShowAddonObjectPropertiesPanel",)


class DroneShowAddonObjectPropertiesPanel(Panel):
    """Custom Blender panel that allows the user to edit the drone show specific
    properties of a Blender object.
    """

    bl_idname = "DATA_PT_skybrush_properties"
    bl_label = "Drone Show"
    bl_options = {"DEFAULT_CLOSED"}

    # The following three settings determine that the panel gets added to the
    # "Object Data Properties" tab in the Properties editor
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        ob = context.object
        layout.label(text="Name of Formation Vertex Group:")

        row = layout.row(align=True)
        row.prop(ob.skybrush, "formation_vertex_group", text="")
        row.operator(
            UseSelectedVertexGroupForFormationOperator.bl_idname, text="Use selected"
        )

        layout.separator()

        layout.operator(UseSelectedVertexGroupForFormationOperator.bl_idname)

    @classmethod
    def poll(cls, context):
        return (
            context.object
            and context.object.type == "MESH"
            and getattr(context.object, "skybrush")
        )
