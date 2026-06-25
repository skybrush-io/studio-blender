import bpy

from sbstudio.plugin.operators import (
    AddDronesSelectedToDroneGroupOperator,
    CreateDroneGroupOperator,
    RemoveDroneGroupOperator,
    RemoveDronesFromDroneGroupOperator,
    SelectDronesFromDroneGroup,
)

__all__ = ("DroneGroupPanel",)


class DroneGroupPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_skybrush_drone_groups_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Drone Groups"
    bl_category = "Formations"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return bpy.context.mode == "OBJECT" and context.scene.skybrush

    def draw(self, context):
        settings = context.scene.skybrush.settings
        layout = self.layout

        layout.use_property_split = False
        layout.use_property_decorate = True

        layout.operator(CreateDroneGroupOperator.bl_idname)

        if settings.drone_collection and len(settings.drone_collection.children) > 0:
            col = layout.column()
            col.label(text="Drone groups:")
            for drone_group_col in settings.drone_collection.children:
                row = layout.row()

                row.prop(drone_group_col, "name", text="", icon="MESH_DATA")

                row.operator(
                    AddDronesSelectedToDroneGroupOperator.bl_idname, icon="ADD", text=""
                ).drone_group = drone_group_col.name

                row.operator(
                    SelectDronesFromDroneGroup.bl_idname,
                    icon="SELECT_SET",
                    text="",
                ).target_collection = drone_group_col.name

                drones_number = "Drones = " + str(len(drone_group_col.objects))
                col = row.column()
                col.scale_x = 0.7
                col.label(text=drones_number)

                row.operator(
                    RemoveDronesFromDroneGroupOperator.bl_idname, icon="TRASH", text=""
                ).drone_group = drone_group_col.name

                row.operator(
                    RemoveDroneGroupOperator.bl_idname, icon="REMOVE", text=""
                ).drone_group = drone_group_col.name
        else:
            row = layout.row()
            row.label(text="No drone groups have been created.")
