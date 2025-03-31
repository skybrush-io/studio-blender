from bpy.props import StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("LitebeeExportOperator",)


#############################################################################
# Operator that allows the user to invoke the Litebee export operation
#############################################################################


class LitebeeExportOperator(ExportOperator):
    """Export object trajectories and light animation into Liteebee's binary format"""

    bl_idname = "export_scene.litebee"
    bl_label = "Export Litebee format"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Litebee files
    filter_glob = StringProperty(default="*.bin", options={"HIDDEN"})
    filename_ext = ".bin"

    def get_format(self) -> FileFormat:
        """Returns the file format that the operator uses. Must be overridden
        in subclasses.
        """
        return FileFormat.LITEBEE

    def get_operator_name(self) -> str:
        return "Litebee exporter"

    def get_settings(self):
        return {
            "redraw": self._get_redraw_setting(),
        }
