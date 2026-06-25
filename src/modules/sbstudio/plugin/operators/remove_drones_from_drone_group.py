import bpy

__all__ = ("RemoveDronesFromDroneGroupOperator",)


class RemoveDronesFromDroneGroupOperator(bpy.types.Operator):
    bl_idname = "skybrush.remove_drones_from_drone_group"
    bl_label = "Remove drones from the drone group."
    bl_options = {"REGISTER", "UNDO"}

    drone_group: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush

    def execute(self, context):
        drone_group_coll = bpy.data.collections[self.drone_group]

        for obj in drone_group_coll.objects:
            drone_group_coll.objects.unlink(obj)

        return {"FINISHED"}
