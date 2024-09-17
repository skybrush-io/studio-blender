from typing import Any, Dict

from bpy.props import IntProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("EVSKYExportOperator",)


####################################################################################
# Operator that allows the user to invoke the EVSKY export operation
####################################################################################


class EVSKYExportOperator(ExportOperator):
    """Export object trajectories and light animation into EVSKY format."""

    bl_idname = "export_scene.evsky"
    bl_label = "Export EVSKY format"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to EVSKY files
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
        return FileFormat.EVSKY

    def get_operator_name(self) -> str:
        return "EVSKY exporter"

    def get_settings(self) -> Dict[str, Any]:
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
        }
