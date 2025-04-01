from typing import Any, Dict

from bpy.props import BoolProperty, IntProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("DDSFExportOperator",)


####################################################################################
# Operator that allows the user to invoke the DDSF export operation
####################################################################################


class DDSFExportOperator(ExportOperator):
    """Export object trajectories and light animation into Depence .ddsf format."""

    bl_idname = "export_scene.ddsf"
    bl_label = "Export Depence .ddsf format"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to DDSF files
    filter_glob = StringProperty(default="*.ddsf", options={"HIDDEN"})
    filename_ext = ".ddsf"

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

    # yaw control enable/disable
    use_yaw_control = BoolProperty(
        name="Export yaw",
        description="Specifies whether the yaw angle of each drone should be controlled during the show",
        default=False,
    )

    def get_format(self) -> FileFormat:
        return FileFormat.DDSF

    def get_operator_name(self) -> str:
        return "Depence .ddsf exporter"

    def get_settings(self) -> Dict[str, Any]:
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "use_yaw_control": self.use_yaw_control,
            "redraw": self._get_redraw_setting(),
        }
