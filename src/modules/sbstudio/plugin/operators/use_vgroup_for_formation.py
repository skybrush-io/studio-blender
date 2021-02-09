from bpy.types import Operator

__all__ = ("UseSelectedVertexGroupForFormationOperator",)


class UseSelectedVertexGroupForFormationOperator(Operator):
    """Blender operator that takes the selected vertex group of the selected
    object and designates it to be used in formations.
    """

    bl_idname = "skybrush.use_selected_vertex_group_for_formation"
    bl_label = "Use Selected Vertex Group for Formation"
    bl_description = (
        "Sets the current vertex group as the one that should be used as "
        "targets when the object is placed in a formation."
    )

    @classmethod
    def poll(cls, context):
        ob = context.object
        vgroups = getattr(ob, "vertex_groups", None)
        return vgroups and len(vgroups) > 0 and vgroups.active

    def execute(self, context):
        ob = context.object
        ob.skybrush.formation_vertex_group = ob.vertex_groups.active.name
        return {"FINISHED"}
