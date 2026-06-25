import bpy

__all__ = ("CreateDroneGroupOperator",)


class CreateDroneGroupOperator(bpy.types.Operator):
    bl_idname = "skybrush.create_drone_group"
    bl_label = "Create a Drone Group"
    bl_options = {"REGISTER", "UNDO"}

    drone_group: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush

    def execute(self, context):
        dronegroup_coll = bpy.data.collections.new("Drone Group")
        context.scene.skybrush.settings.drone_collection.children.link(dronegroup_coll)

        return {"FINISHED"}
