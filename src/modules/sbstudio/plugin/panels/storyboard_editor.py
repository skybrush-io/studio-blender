from bpy.types import Panel

from typing import Optional

from sbstudio.plugin.model.storyboard import Storyboard
from sbstudio.plugin.operators import (
    CreateNewStoryboardEntryOperator,
    MoveStoryboardEntryDownOperator,
    MoveStoryboardEntryUpOperator,
    RecalculateTransitionsOperator,
    RemoveStoryboardEntryOperator,
    SelectStoryboardEntryForCurrentFrameOperator,
    SetStoryboardEntryEndFrameOperator,
    SetStoryboardEntryStartFrameOperator,
    UpdateTimeMarkersFromStoryboardOperator,
)


class StoryboardEditor(Panel):
    """Custom Blender panel that allows the user to edit the storyboard of the
    current drone show.
    """

    bl_idname = "OBJECT_PT_skybrush_storyboard_editor"
    bl_label = "Storyboard"

    # The following three settings determine that the storyboard editor gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Formations"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        storyboard: Optional[Storyboard] = scene.skybrush.storyboard
        if not storyboard:
            return

        row = layout.row()

        col = row.column()
        col.template_list(
            "UI_UL_list",
            "OBJECT_PT_skybrush_storyboard_editor",
            storyboard,
            "entries",
            storyboard,
            "active_entry_index",
            maxrows=6,
            sort_lock=True,
        )

        col = row.column(align=True)
        col.operator(CreateNewStoryboardEntryOperator.bl_idname, icon="ADD", text="")
        col.operator(RemoveStoryboardEntryOperator.bl_idname, icon="REMOVE", text="")
        col.separator()
        col.operator(
            SelectStoryboardEntryForCurrentFrameOperator.bl_idname,
            icon="EMPTY_SINGLE_ARROW",
            text="",
        )
        col.separator()
        col.operator(MoveStoryboardEntryUpOperator.bl_idname, icon="TRIA_UP", text="")
        col.operator(
            MoveStoryboardEntryDownOperator.bl_idname, icon="TRIA_DOWN", text=""
        )

        #####################################################################

        entry = storyboard.active_entry
        if entry is not None:
            col = layout.column()
            col.prop(entry, "formation")
            row = col.row()
            row.prop(entry, "frame_start")
            row.separator()
            row.operator(
                SetStoryboardEntryStartFrameOperator.bl_idname,
                icon="TRIA_LEFT",
                text="",
            )
            col.prop(entry, "duration")
            row = col.row()
            row.prop(entry, "frame_end")
            row.separator()
            row.operator(
                SetStoryboardEntryEndFrameOperator.bl_idname,
                icon="TRIA_LEFT",
                text="",
            )
            col.prop(entry, "purpose")
            col.prop(entry, "is_name_customized")
            col.popover(
                "OBJECT_PT_skybrush_transition_editor_pre",
                icon="TRACKING_CLEAR_BACKWARDS",
            )
            col.popover(
                "OBJECT_PT_skybrush_transition_editor_post",
                icon="TRACKING_CLEAR_FORWARDS",
            )

        #####################################################################

        layout.separator()

        col = layout.column()

        col.emboss = "NORMAL"
        col.operator_menu_enum(
            RecalculateTransitionsOperator.bl_idname, "scope", icon="SHADERFX"
        )

        #####################################################################

        row = layout.row(align=True)

        row.operator(
            UpdateTimeMarkersFromStoryboardOperator.bl_idname,
            icon="ANCHOR_CENTER",
            text="Update Time Markers",
        )
