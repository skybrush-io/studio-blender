from bpy.types import Context, Operator

from sbstudio.plugin.model.drone_groups import get_drone_groups

__all__ = ("CreateDroneGroupOperator",)


class CreateDroneGroupOperator(Operator):
    """Creates a new drone group in the drone groups collection."""

    bl_idname = "skybrush.create_drone_group"
    bl_label = "Create a Drone Group"
    bl_description = "Create a new drone group in the drone groups collection"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: Context):
        return context.scene.skybrush

    def execute(self, context: Context):
        drone_groups = get_drone_groups(context=context)
        drone_groups.add_new_group(select=True)
        return {"FINISHED"}
