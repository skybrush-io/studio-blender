import bpy
import os

from bpy.props import BoolProperty, StringProperty, IntProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.model.file_formats import FileFormat
from sbstudio.plugin.props.frame_range import FrameRangeProperty

from .utils import export_show_to_file_using_api

__all__ = ("SkybrushPDFExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .pdf plot export operation
#############################################################################


class SkybrushPDFExportOperator(Operator, ExportHelper):
    """Export object trajectories into validation plots stored in a .pdf file"""

    bl_idname = "export_scene.skybrush_pdf"
    bl_label = "Export Skybrush PDF"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to .pdf files
    filter_glob = StringProperty(default="*.pdf", options={"HIDDEN"})
    filename_ext = ".pdf"

    # output all objects or only selected ones
    export_selected = BoolProperty(
        name="Export selected drones only",
        default=False,
        description=(
            "Export only the selected drones. "
            "Uncheck to export all drones, irrespectively of the selection."
        ),
    )

    # frame range
    frame_range = FrameRangeProperty(default="RENDER")

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
            "Include position plot. "
            "Uncheck to exclude position plot from the output."
        ),
    )
    plot_vel = BoolProperty(
        name="Plot velocities",
        default=True,
        description=(
            "Include velocity plot. "
            "Uncheck to exclude velocity plot from the output."
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

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        plots = {
            "pos": self.plot_pos,
            "vel": self.plot_vel,
            "nn": self.plot_nn,
            "nnall": self.plot_nnall,
            "indiv": self.plot_indiv,
        }
        plots = ["stats"] + [key for key, value in plots.items() if value]
        settings = {
            "export_selected": self.export_selected,
            "frame_range": self.frame_range,
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "plots": plots,
        }

        if os.path.basename(filepath).lower() == self.filename_ext.lower():
            self.report({"ERROR_INVALID_INPUT"}, "Filename must not be empty")
            return {"CANCELLED"}

        try:
            with call_api_from_blender_operator(
                self, ".pdf validation plot exporter"
            ) as api:
                export_show_to_file_using_api(
                    api, context, settings, filepath, FileFormat.PDF
                )
        except Exception:
            return {"CANCELLED"}

        self.report({"INFO"}, "Export successful")
        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}.pdf"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
