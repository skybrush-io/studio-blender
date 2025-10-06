from bpy.types import Panel

from sbstudio.plugin.menus import GenerateMarkersMenu
from sbstudio.plugin.operators import (
    CreateFormationOperator,
    CreateTakeoffGridOperator,
    DeselectFormationOperator,
    GetFormationStatisticsOperator,
    LandOperator,
    RemoveFormationOperator,
    ReorderFormationMarkersOperator,
    ReturnToHomeOperator,
    SelectFormationOperator,
    TakeoffOperator,
    UpdateFormationOperator,
    AppendFormationToStoryboardOperator,
)
from sbstudio.plugin.utils.warnings import (
    draw_bad_shader_color_source_warning,
    draw_formation_size_warning,
    draw_version_warning,
)

__all__ = ("FormationsPanel",)


class FormationsPanel(Panel):
    """Custom Blender panel that allows the user to create new formations or
    update existing ones.
    """

    bl_idname = "OBJECT_PT_skybrush_formations_panel"
    bl_label = "Formations"

    # The following three settings determine that the Formations panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Formations"

    @classmethod
    def poll(cls, context):
        return context.scene.skybrush.formations

    def draw(self, context):
        formations = context.scene.skybrush.formations
        if not formations:
            return

        layout = self.layout

        draw_version_warning(context, layout)
        draw_bad_shader_color_source_warning(context, layout)

        layout.operator(CreateTakeoffGridOperator.bl_idname, icon="ADD")

        row = layout.row(align=True)
        row.operator(TakeoffOperator.bl_idname, text="Takeoff", icon="TRIA_UP_BAR")
        row.operator(ReturnToHomeOperator.bl_idname, text="RTH", icon="HOME")
        row.operator(LandOperator.bl_idname, text="Land", icon="TRIA_DOWN_BAR")

        layout.separator()

        row = layout.row(align=True)
        row.prop(formations, "selected", text="")
        row.operator(CreateFormationOperator.bl_idname, icon="ADD", text="")
        row.operator(RemoveFormationOperator.bl_idname, icon="X", text="")

        row = layout.row(align=True)
        row.operator(SelectFormationOperator.bl_idname, text="Select")
        row.operator(DeselectFormationOperator.bl_idname, text="Deselect")
        row.operator(GetFormationStatisticsOperator.bl_idname, text="Stats")

        draw_formation_size_warning(context, layout)

        row = layout.row(align=True)
        row.menu(
            GenerateMarkersMenu.bl_idname, text="Generate Markers", icon="SHADERFX"
        )

        row = layout.row(align=True)
        row.operator(
            AppendFormationToStoryboardOperator.bl_idname,
            text="Append",
            icon="FORWARD",
        )

        row = layout.row(align=True)
        row.operator(
            UpdateFormationOperator.bl_idname, text="Update", icon="FILE_REFRESH"
        )
        row.operator_menu_enum(
            ReorderFormationMarkersOperator.bl_idname,
            "type",
            icon="SORTSIZE",
            text="Reorder",
        )

        row = layout.row()
        row.prop(formations, "order_overlay_enabled")
