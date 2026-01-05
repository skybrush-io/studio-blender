from typing import Any

from bpy.props import BoolProperty, IntProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("SkybrushSKYCAndPDFExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .skyc export operation
#############################################################################


class SkybrushSKYCAndPDFExportOperator(ExportOperator):
    """Export object trajectories and light animation into .skyc and .pdf formats in one request"""

    bl_idname = "export_scene.skybrush_and_pdf"
    bl_label = "Export Skybrush SKYC+PDF"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to the zipped Skybrush files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    ##################################################
    # properties inherited from SkybrushExportOperator

    output_fps = IntProperty(
        name="Trajectory FPS",
        default=4,
        description="Number of samples to take from trajectories per second",
    )

    light_output_fps = IntProperty(
        name="Light FPS",
        default=4,
        description="Number of samples to take from light programs per second",
    )

    use_pyro_control = BoolProperty(
        name="Export pyro (PRO)",
        description="Specifies whether the pyro program of each drone should be included in the show",
        default=False,
    )

    use_yaw_control = BoolProperty(
        name="Export yaw (PRO)",
        description="Specifies whether the yaw angle of each drone should be controlled during the show",
        default=False,
    )

    export_cameras = BoolProperty(
        name="Export cameras",
        description="Specifies whether cameras defined in Blender should be exported into the show file",
        default=False,
    )

    #####################################################
    # properties inherited from SkybrushPDFExportOperator

    plot_stats = BoolProperty(
        name="Plot flight report",
        default=True,
        description=("Include flight statistics and validation report (required)."),
    )
    plot_pos = BoolProperty(
        name="Plot positions",
        default=True,
        description=(
            "Include position plot. Uncheck to exclude position plot from the output."
        ),
    )
    plot_vel = BoolProperty(
        name="Plot velocities",
        default=True,
        description=(
            "Include velocity plot. Uncheck to exclude velocity plot from the output."
        ),
    )
    plot_drift = BoolProperty(
        name="Plot projected drift",
        default=True,
        description=(
            "Include projected drift plot. Uncheck to exclude projected drift plot from the output."
        ),
    )
    plot_nn = BoolProperty(
        name="Plot nearest neighbor",
        default=True,
        description=(
            "Include nearest neighbor plot. "
            "Uncheck to exclude nearest neighbor plot from the output."
        ),
    )
    plot_nnall = BoolProperty(
        name="Plot all nearest neighbors",
        default=False,
        description=(
            "Include all nearest neighbors plot. "
            "Uncheck to exclude all nearest neighbor plot from the output."
        ),
    )
    plot_indiv = BoolProperty(
        name="Create individual drone plots",
        default=False,
        description=(
            "Include individual drone plots."
            "Uncheck to exclude per-drone plots from the output."
        ),
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, "export_selected")
        layout.prop(self, "frame_range")
        layout.prop(self, "redraw")
        layout.prop(self, "output_fps")
        layout.prop(self, "light_output_fps")

        column = layout.column(align=True)
        column.label(text="SKYC export features:")
        column.prop(self, "export_cameras")
        column.prop(self, "use_pyro_control")
        column.prop(self, "use_yaw_control")

        column = layout.column(align=True)
        column.label(text="PDF export features:")
        row = column.row()
        row.prop(self, "plot_stats")
        row.enabled = False
        column.prop(self, "plot_pos")
        column.prop(self, "plot_vel")
        column.prop(self, "plot_drift")
        column.prop(self, "plot_nn")
        column.prop(self, "plot_nnall")
        column.prop(self, "plot_indiv")

    def get_format(self) -> FileFormat:
        return FileFormat.SKYC_AND_PDF

    def get_operator_name(self) -> str:
        return ".skyc + .pdf exporter"

    def get_settings(self) -> dict[str, Any]:
        plots = {
            "stats": self.plot_stats,
            "pos": self.plot_pos,
            "vel": self.plot_vel,
            "drift": self.plot_drift,
            "nn": self.plot_nn,
            "nnall": self.plot_nnall,
            "indiv": self.plot_indiv,
        }
        plots = [key for key, value in plots.items() if value]

        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "use_pyro_control": self.use_pyro_control,
            "use_yaw_control": self.use_yaw_control,
            "export_cameras": self.export_cameras,
            "plots": plots,
        }
