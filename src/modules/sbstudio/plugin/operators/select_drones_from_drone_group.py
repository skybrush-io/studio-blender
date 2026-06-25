import bpy

__all__ = ("SelectDronesFromDroneGroup",)


class SelectDronesFromDroneGroup(bpy.types.Operator):
    bl_idname = "skybrush.select_drones_from_drone_group"
    bl_label = "Select the objects from the indicated drone group."
    bl_options = {"REGISTER", "UNDO"}

    target_collection: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush

    def execute(self, context):
        objs = bpy.data.collections[self.target_collection].objects

        if objs:
            if bpy.context.selected_objects:
                bpy.context.selected_objects[0].select_set(True)
                bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
                bpy.ops.object.select_all()

            for ob in objs:
                ob.select_set(True)

        return {"FINISHED"}
