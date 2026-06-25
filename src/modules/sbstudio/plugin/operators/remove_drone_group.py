import bpy

__all__ = ("RemoveDroneGroupOperator",)


class RemoveDroneGroupOperator(bpy.types.Operator):
    bl_idname = "skybrush.remove_drone_group"
    bl_label = "Remove Drone Group"
    bl_options = {"REGISTER", "UNDO"}

    drone_group: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush

    def execute(self, context):
        bpy.data.collections.remove(bpy.data.collections[self.drone_group])

        return {"FINISHED"}
