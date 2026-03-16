from typing import Any

from bpy.props import BoolProperty, IntProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("FinaleCSVExportOperator",)


####################################################################################
# Operator that allows the user to invoke the Finale3D DIY CSV export operation
####################################################################################


class FinaleCSVExportOperator(ExportOperator):
    """Export object trajectories and light animation into Finale 3D DIY .csv format."""

    bl_idname = "export_scene.finale_csv"
    bl_label = "Export Finale 3D DIY CSV format"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Finale3D CSV files
    filter_glob = StringProperty(default="*.csv", options={"HIDDEN"})
    filename_ext = ".csv"

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
        name="Export yaw (PRO)",
        description="Specifies whether the yaw angle of each drone should be controlled during the show",
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
        column.prop(self, "use_yaw_control")

    def get_format(self) -> FileFormat:
        return FileFormat.FINALE_CSV

    def get_operator_name(self) -> str:
        return "Finale 3D DIY CSV exporter"

    def get_settings(self) -> dict[str, Any]:
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "use_yaw_control": self.use_yaw_control,
        }
