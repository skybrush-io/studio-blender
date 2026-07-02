import bpy
from bpy.types import Context, Operator

from sbstudio.plugin.constants import Collections

__all__ = ("CreateDroneGroupOperator",)


class CreateDroneGroupOperator(Operator):
    bl_idname = "skybrush.create_drone_group"
    bl_label = "Create a Drone Group"
    bl_description = "Create a new drone group in the drone groups collection"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: Context):
        return context.scene.skybrush

    def execute(self, context: Context):
        dronegroup_coll = bpy.data.collections.new("New Drone Group")
        main_coll = Collections.find_drone_groups(create=True)
        main_coll.children.link(dronegroup_coll)
        return {"FINISHED"}
