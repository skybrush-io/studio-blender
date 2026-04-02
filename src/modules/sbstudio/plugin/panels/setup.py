from bpy.types import Context, Panel

from sbstudio.plugin.operators import RunAllMigrationOperators, SetupSceneOperator
from sbstudio.plugin.utils.warnings import (
    draw_bad_shader_color_source_warning,
    draw_version_warning,
)

__all__ = ("SetupPanel",)


class SetupPanel(Panel):
    """Custom Blender panel containing buttons for the general setup procedure of the
    Skybrush Studio add-on.
    """

    bl_idname = "OBJECT_PT_skybrush_setup_panel"
    bl_label = "Setup"

    # The following three settings determine that the show control panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Skybrush"

    def draw(self, context: Context):
        scene = context.scene
        settings = scene.skybrush.settings

        if not settings:
            return

        layout = self.layout

        draw_version_warning(context, layout)
        draw_bad_shader_color_source_warning(context, layout)

        layout.operator(
            SetupSceneOperator.bl_idname,
            icon="TOOL_SETTINGS",
        )
        layout.operator(RunAllMigrationOperators.bl_idname, icon="FILE_REFRESH")
