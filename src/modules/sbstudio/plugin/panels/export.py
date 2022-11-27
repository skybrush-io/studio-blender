import bpy

from bpy.types import Panel

from sbstudio.plugin.operators import (
    SkybrushExportOperator,
    SkybrushCSVExportOperator,
    SkybrushPDFExportOperator,
)

__all__ = ("ExportPanel",)


class ExportPanel(Panel):
    """Custom Blender panel that allows the user to export the current show into
    one of the supported formats.
    """

    bl_idname = "OBJECT_PT_skybrush_export_panel"
    bl_label = "Export"

    # The following three settings determine that the Export panel gets
    # added to the sidebar of the 3D view
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Safety & Export"

    def draw(self, context):
        scene = context.scene
        settings = scene.skybrush.settings

        layout = self.layout

        if settings:
            layout.prop(settings, "show_type")

        layout.operator(SkybrushExportOperator.bl_idname, text="Export to .skyc")
        layout.operator(SkybrushCSVExportOperator.bl_idname, text="Export to .csv")
        layout.operator(
            SkybrushPDFExportOperator.bl_idname, text="Export to validation .pdf"
        )
