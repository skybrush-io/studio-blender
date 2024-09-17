from bpy.types import Panel

from sbstudio.model.file_formats import FileFormat, get_supported_file_formats
from sbstudio.plugin.operators import (
    DACExportOperator,
    DrotekExportOperator,
    DSSPathExportOperator,
    DSSPath3ExportOperator,
    EVSKYExportOperator,
    LitebeeExportOperator,
    RefreshFileFormatsOperator,
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

        formats = get_supported_file_formats()

        for format in formats:
            if format is FileFormat.SKYC:
                layout.operator(
                    SkybrushExportOperator.bl_idname, text="Export to .skyc"
                )
            elif format is FileFormat.CSV:
                layout.operator(
                    SkybrushCSVExportOperator.bl_idname, text="Export to .csv"
                )
            elif format is FileFormat.DAC:
                layout.operator(DACExportOperator.bl_idname, text="Export to .dac")
            elif format is FileFormat.DROTEK:
                layout.operator(
                    DrotekExportOperator.bl_idname, text="Export to Drotek format"
                )
            elif format is FileFormat.DSS:
                layout.operator(
                    DSSPathExportOperator.bl_idname, text="Export to DSS PATH format"
                )
                layout.operator(
                    DSSPath3ExportOperator.bl_idname, text="Export to DSS PATH3 format"
                )
            elif format is FileFormat.EVSKY:
                layout.operator(
                    EVSKYExportOperator.bl_idname, text="Export to EVSKY format"
                )
            elif format is FileFormat.LITEBEE:
                layout.operator(
                    LitebeeExportOperator.bl_idname, text="Export to Litebee format"
                )
            elif format is FileFormat.PDF:
                layout.operator(
                    SkybrushPDFExportOperator.bl_idname, text="Export validation report"
                )

        layout.separator()

        layout.operator(
            RefreshFileFormatsOperator.bl_idname, text="Refresh file formats"
        )
