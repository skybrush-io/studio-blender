from typing import Any

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

    # pyro control enable/disable
    use_pyro_control = BoolProperty(
        name="Export pyro (PRO)",
        description="Specifies whether the pyro program of each drone should be included in the show",
        default=False,
    )

    # yaw control enable/disable
    use_yaw_control = BoolProperty(
        name="Export yaw (PRO)",
        description="Specifies whether the yaw angle of each drone should be controlled during the show",
        default=False,
    )

    # yaw control enable/disable
    export_cameras = BoolProperty(
        name="Export cameras",
        description="Specifies whether cameras defined in Blender should be exported into the show file",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, "export_selected")
        layout.prop(self, "frame_range")
        layout.prop(self, "redraw")
        layout.prop(self, "output_fps")
        layout.prop(self, "light_output_fps")

        layout.separator()

        column = layout.column(align=True)
        column.prop(self, "export_cameras")
        column.prop(self, "use_pyro_control")
        column.prop(self, "use_yaw_control")

    def get_format(self) -> FileFormat:
        """Returns the file format that the operator uses. Must be overridden
        in subclasses.
        """
        return FileFormat.SKYC

    def get_operator_name(self) -> str:
        return ".skyc exporter"

    def get_settings(self) -> dict[str, Any]:
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "use_pyro_control": self.use_pyro_control,
            "use_yaw_control": self.use_yaw_control,
            "export_cameras": self.export_cameras,
        }
