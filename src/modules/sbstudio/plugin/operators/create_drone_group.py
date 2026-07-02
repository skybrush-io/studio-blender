import bpy

from sbstudio.plugin.constants import Collections

__all__ = ("CreateDroneGroupOperator",)


class CreateDroneGroupOperator(bpy.types.Operator):
    bl_idname = "skybrush.create_drone_group"
    bl_label = "Create a Drone Group"
    bl_description = "Create a new drone group in the Drone Groups collection"
    bl_options = {"REGISTER", "UNDO"}

    drone_group: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush

    def execute(self, context):
        dronegroup_coll = bpy.data.collections.new("Drone Group")
        main_coll = Collections.find_drone_groups(create=True)
        main_coll.children.link(dronegroup_coll)
        return {"FINISHED"}
