import bpy
from bpy.props import IntProperty
from bpy.types import Context, Panel

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.operators import (
    AddSelectedDronesToDroneGroupOperator,
    ClearDroneGroupOperator,
    CreateDroneGroupOperator,
    RemoveDroneGroupOperator,
    SelectDronesFromDroneGroup,
)

__all__ = ("DroneGroupsPanel",)


class DroneGroupsPanel(Panel):
    """Custom Blender panel that allows the user to manage drone groups."""

    bl_idname = "OBJECT_PT_skybrush_drone_groups_panel"
    bl_label = "Drone Groups"

    # The following three settings determine that the storyboard editor gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Skybrush"

    active_index = IntProperty(default=0)

    @classmethod
    def poll(cls, context: Context):
        return bpy.context.mode == "OBJECT" and context.scene.skybrush

    def draw(self, context: Context):
        scene = context.scene
        settings = scene.skybrush.settings

        layout = self.layout
        # layout.use_property_split = True
        # layout.use_property_decorate = False

        layout.prop(settings, "drone_group_collection", text="Stored in")

        row = layout.row()

        group_collection = Collections.find_drone_groups(create=False)

        col = row.column()
        col.template_list(
            "SKYBRUSH_UL_dronegrouplist",
            "OBJECT_PT_skybrush_storyboard_editor",
            group_collection,
            "children",
            context.scene.skybrush.drone_groups,
            "active_group_index",
            maxrows=6,
            sort_lock=True,
        )

        col = row.column(align=True)
        col.operator(CreateDroneGroupOperator.bl_idname, icon="ADD", text="")
        col.operator(RemoveDroneGroupOperator.bl_idname, icon="REMOVE", text="")

        row = layout.row(align=True)
        row.operator(
            AddSelectedDronesToDroneGroupOperator.bl_idname,
            text="Add",
            icon="ADD",
        )
        row.operator(
            SelectDronesFromDroneGroup.bl_idname, text="Select", icon="SELECT_SET"
        )
        row.operator(
            ClearDroneGroupOperator.bl_idname,
            text="Clear",
            icon="TRASH",
        )
