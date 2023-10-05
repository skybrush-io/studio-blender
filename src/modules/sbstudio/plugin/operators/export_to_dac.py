import bpy

from bpy.props import StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("DACExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .dac export operation
#############################################################################


class DACExportOperator(ExportOperator):
    """Export object trajectories and light animation into .dac format."""

    bl_idname = "export_scene.dac"
    bl_label = "Export DAC"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to .dac files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    def get_format(self) -> FileFormat:
        """Returns the file format that the operator uses. Must be overridden
        in subclasses.
        """
        return FileFormat.DAC

    def get_operator_name(self) -> str:
        return ".dac exporter"

    def get_settings(self):
        return {"output_fps": 30, "light_output_fps": 30}
