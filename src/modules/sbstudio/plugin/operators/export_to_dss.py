from typing import Any, Dict

from bpy.props import StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("DSSPathExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .dac export operation
#############################################################################


class DSSPathExportOperator(ExportOperator):
    """Export object trajectories and light animation into DSS PATH format."""

    bl_idname = "export_scene.dss_path"
    bl_label = "Export DSS"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to DSS PATH files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    def get_format(self) -> FileFormat:
        return FileFormat.DSS

    def get_operator_name(self) -> str:
        return "DSS PATH exporter"

    def get_settings(self) -> Dict[str, Any]:
        return {}
