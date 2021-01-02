from bpy.types import Panel

from sbstudio.plugin.operators import (
    CreateNewStoryboardEntryOperator,
    RecalculateTransitionsOperator,
    RemoveStoryboardEntryOperator,
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
    bl_category = "Show Design"

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
        row.enabled = entry is not None
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname, text="Previous to Selected"
        )
        params.scope = "TO_SELECTED"

        row = col.row()
        row.enabled = entry is not None and not is_last
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname, text="Selected to Next"
        )
        params.scope = "FROM_SELECTED"

        row = col.row()
        row.enabled = entry is not None and not is_last
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname, text="Selected to End"
        )
        params.scope = "FROM_SELECTED_TO_END"

        row = col.row()
        row.enabled = len(storyboard.entries) > 0
        params = row.operator(
            RecalculateTransitionsOperator.bl_idname, text="Entire Storyboard"
        )
        params.scope = "ALL"
