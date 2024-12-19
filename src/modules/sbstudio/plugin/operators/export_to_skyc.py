from bpy.props import BoolProperty, IntProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("SkybrushExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .skyc export operation
#############################################################################


class SkybrushExportOperator(ExportOperator):
    """Export object trajectories and light animation into the Skybrush compiled format (.skyc)"""

    bl_idname = "export_scene.skybrush"
    bl_label = "Export Skybrush SKYC"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush files
    filter_glob = StringProperty(default="*.skyc", options={"HIDDEN"})
    filename_ext = ".skyc"

    # output trajectory frame rate
    output_fps = IntProperty(
        name="Trajectory FPS",
        default=4,
        description="Number of samples to take from trajectories per second",
    )

    # output light program frame rate
    light_output_fps = IntProperty(
        name="Light FPS",
        default=4,
        description="Number of samples to take from light programs per second",
    )

    # yaw control enable/disable
    use_yaw_control = BoolProperty(
        name="Export yaw",
        description="Specifies whether the yaw angle of each drone should be controlled during the show",
        default=False,
    )

    # yaw control enable/disable
    export_cameras = BoolProperty(
        name="Export cameras",
        description="Specifies whether cameras defined in Blender should be exported into the show file",
        default=False,
    )

    def get_format(self) -> FileFormat:
        """Returns the file format that the operator uses. Must be overridden
        in subclasses.
        """
        return FileFormat.SKYC

    def get_operator_name(self) -> str:
        return ".skyc exporter"

    def get_settings(self):
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "use_yaw_control": self.use_yaw_control,
            "export_cameras": self.export_cameras,
        }
