from bpy.types import Panel

from sbstudio.plugin.operators import (
    CreateNewStoryboardEntryOperator,
    MoveStoryboardEntryDownOperator,
    MoveStoryboardEntryUpOperator,
    RecalculateTransitionsOperator,
    RemoveStoryboardEntryOperator,
    SelectStoryboardEntryForCurrentFrameOperator,
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
        storyboard = scene.skybrush.storyboard
        if not storyboard:
            return

        entry = storyboard.active_entry
        is_last = (
            entry is None
            or storyboard.active_entry_index == len(storyboard.entries) - 1
        )

        row = layout.row()

        col = row.column()
        col.template_list(
            "UI_UL_list",
            "OBJECT_PT_skybrush_storyboard_editor",
            storyboard,
            "entries",
            storyboard,
            "active_entry_index",
            maxrows=10,
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

        if entry is not None:
            col = layout.column()
            col.prop(entry, "formation")
            col.prop(entry, "frame_start")
            col.prop(entry, "duration")
            col.prop(entry, "transition_type")
            col.prop(entry, "is_name_customized")

        layout.separator()

        col = layout.column()

        col.label(text="Recalculate Transitions")

        row = col.row()
        index = storyboard.get_index_of_entry_containing_frame(scene.frame_current)
        row.enabled = index < 0
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname,
            text="Current Frame",
            icon="EMPTY_SINGLE_ARROW",
        )
        params.scope = "CURRENT_FRAME"

        row = col.row()
        row.enabled = entry is not None
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname,
            text="Previous to Selected",
            icon="TRACKING_BACKWARDS_SINGLE",
        )
        params.scope = "TO_SELECTED"

        row = col.row()
        row.enabled = entry is not None and not is_last
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname,
            text="Selected to Next",
            icon="TRACKING_FORWARDS_SINGLE",
        )
        params.scope = "FROM_SELECTED"

        row = col.row()
        row.enabled = entry is not None and not is_last
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname,
            text="Selected to End",
            icon="TRACKING_FORWARDS",
        )
        params.scope = "FROM_SELECTED_TO_END"

        row = col.row()
        row.enabled = len(storyboard.entries) > 0
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname,
            text="Entire Storyboard",
            icon="SEQUENCE",
        )
        params.scope = "ALL"
