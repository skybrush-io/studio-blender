from bpy.types import Panel


class StoryboardEditor(Panel):
    """Custom Blender panel that allows the user to edit the storyboard of the
    current drone show.
    """

    bl_idname = "OBJECT_PT_skybrush_storyboard_editor"
    bl_label = "Storyboard"

    # The following three settings determine that the storyboard editor gets
    # added to the "Scene" tab in the properties panel
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        storyboard = scene.skybrush.storyboard
        if not storyboard:
            return

        entry = storyboard.active_entry

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
        col.operator("skybrush.create_new_storyboard_entry", icon="ADD", text="")
        col.operator("skybrush.remove_storyboard_entry", icon="REMOVE", text="")

        if entry is not None:
            col = layout.column()
            col.prop(entry, "formation")
            col.prop(entry, "frame_start")
            col.prop(entry, "duration")
            col.prop(entry, "is_name_customized")

        col = layout.column()
        col.operator("skybrush.recalculate_transitions")
