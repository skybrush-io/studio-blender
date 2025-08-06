from bpy.types import Panel

from sbstudio.model.file_formats import FileFormat, get_supported_file_formats
from sbstudio.plugin.operators import (
    DACExportOperator,
    DDSFExportOperator,
    DrotekExportOperator,
    DSSPathExportOperator,
    DSSPath3ExportOperator,
    EVSKYExportOperator,
    LitebeeExportOperator,
    RefreshFileFormatsOperator,
    SkybrushExportOperator,
    SkybrushCSVExportOperator,
    SkybrushPDFExportOperator,
    SkybrushSKYCAndPDFExportOperator,
    VVIZExportOperator,
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
        layout = self.layout

        formats = get_supported_file_formats()

        # in-house formats
        if FileFormat.SKYC in formats:
            layout.operator(
                SkybrushExportOperator.bl_idname, text="Export to Skybrush .skyc"
            )
        if FileFormat.CSV in formats:
            layout.operator(
                SkybrushCSVExportOperator.bl_idname, text="Export to Skybrush .csv"
            )
        if FileFormat.PDF in formats:
            layout.operator(
                SkybrushPDFExportOperator.bl_idname,
                text="Export validation report .pdf",
            )
        if FileFormat.SKYC_AND_PDF in formats:
            layout.operator(
                SkybrushSKYCAndPDFExportOperator.bl_idname,
                text="Export to .skyc + .pdf",
            )

        layout.separator()
        needs_separator: bool = False

        # external formats
        if FileFormat.DAC in formats:
            layout.operator(DACExportOperator.bl_idname, text="Export to HG .dac")
            needs_separator = True
        if FileFormat.DROTEK in formats:
            layout.operator(
                DrotekExportOperator.bl_idname, text="Export to Drotek .json"
            )
            needs_separator = True
        if FileFormat.DSS in formats:
            layout.operator(DSSPathExportOperator.bl_idname, text="Export to DSS .path")
            layout.operator(
                DSSPath3ExportOperator.bl_idname, text="Export to DSS .path3"
            )
            needs_separator = True
        if FileFormat.EVSKY in formats:
            layout.operator(EVSKYExportOperator.bl_idname, text="Export to EVSKY .essp")
            needs_separator = True
        if FileFormat.LITEBEE in formats:
            layout.operator(
                LitebeeExportOperator.bl_idname, text="Export to Litebee .bin"
            )
            needs_separator = True

        if needs_separator:
            layout.separator()
            needs_separator = False

        if FileFormat.VVIZ in formats:
            layout.operator(
                VVIZExportOperator.bl_idname, text="Export to Finale 3D .vviz"
            )
            needs_separator = True
        if FileFormat.DDSF in formats:
            layout.operator(
                DDSFExportOperator.bl_idname, text="Export to Depence .ddsf"
            )
            needs_separator = True

        if needs_separator:
            layout.separator()
            needs_separator = False

        layout.operator(
            RefreshFileFormatsOperator.bl_idname, text="Refresh file formats (PRO)"
        )
