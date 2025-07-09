from typing import Any

from bpy.props import BoolProperty, StringProperty, IntProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("SkybrushPDFExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .pdf plot export operation
#############################################################################


class SkybrushPDFExportOperator(ExportOperator):
    """Export object trajectories into validation plots stored in a .pdf file"""

    bl_idname = "export_scene.skybrush_pdf"
    bl_label = "Export Skybrush PDF"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to .pdf files
    filter_glob = StringProperty(default="*.pdf", options={"HIDDEN"})
    filename_ext = ".pdf"

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

        layout.separator()

        column = layout.column(align=True)
        column.prop(self, "plot_pos")
        column.prop(self, "plot_vel")
        column.prop(self, "plot_drift")
        column.prop(self, "plot_nn")
        column.prop(self, "plot_nnall")
        column.prop(self, "plot_indiv")

    def get_format(self) -> FileFormat:
        """Returns the file format that the operator uses. Must be overridden
        in subclasses.
        """
        return FileFormat.PDF

    def get_operator_name(self) -> str:
        return ".pdf validation plot exporter"

    def get_settings(self) -> dict[str, Any]:
        plots = {
            "pos": self.plot_pos,
            "vel": self.plot_vel,
            "drift": self.plot_drift,
            "nn": self.plot_nn,
            "nnall": self.plot_nnall,
            "indiv": self.plot_indiv,
        }
        plots = ["stats"] + [key for key, value in plots.items() if value]

        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "plots": plots,
        }
