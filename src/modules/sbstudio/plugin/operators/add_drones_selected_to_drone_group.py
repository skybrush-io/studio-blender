import bpy

__all__ = ("AddDronesSelectedToDroneGroupOperator",)


class AddDronesSelectedToDroneGroupOperator(bpy.types.Operator):
    bl_idname = "skybrush.add_drones_selected_to_drone_group"
    bl_label = "Add Drones Selected"
    bl_options = {"REGISTER", "UNDO"}

    drone_group: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush and context.selected_objects

    def execute(self, context):
        scn = context.scene
        main_coll = scn.skybrush.settings.drone_collection
        drone_group_coll = bpy.data.collections[self.drone_group]

        for obj in context.selected_objects:
            if (
                obj.name in main_coll.objects
                and obj.name not in drone_group_coll.objects
            ):
                drone_group_coll.objects.link(obj)

        return {"FINISHED"}
