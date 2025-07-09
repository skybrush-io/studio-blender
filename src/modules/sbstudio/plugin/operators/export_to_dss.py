from typing import Any

from bpy.props import IntProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("DSSPathExportOperator", "DSSPath3ExportOperator")


####################################################################################
# Operator that allows the user to invoke the DSS .path and .path3 export operations
####################################################################################


class DSSPathExportOperator(ExportOperator):
    """Export object trajectories and light animation into DSS PATH format."""

    bl_idname = "export_scene.dss_path"
    bl_label = "Export DSS PATH"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to DSS PATH files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    def get_format(self) -> FileFormat:
        return FileFormat.DSS

    def get_operator_name(self) -> str:
        return "DSS PATH exporter"

    def get_settings(self) -> dict[str, Any]:
        return {}


class DSSPath3ExportOperator(ExportOperator):
    """Export object trajectories and light animation into DSS PATH3 format."""

    bl_idname = "export_scene.dss_path3"
    bl_label = "Export DSS PATH3"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to DSS PATH3 files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    # output trajectory frame rate
    output_fps = IntProperty(
        name="Trajectory FPS",
        default=4,
        description="Number of samples to take from trajectories per second",
    )

    # output light program frame rate
    light_output_fps = IntProperty(
        name="Light FPS",
        default=24,
        description="Number of samples to take from light programs per second",
    )

    def get_format(self) -> FileFormat:
        return FileFormat.DSS3

    def get_operator_name(self) -> str:
        return "DSS PATH3 exporter"

    def get_settings(self) -> dict[str, Any]:
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
        }
