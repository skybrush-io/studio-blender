import bpy
import os

from bpy.props import BoolProperty, StringProperty, IntProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.plugin.model.file_formats import FileFormat
from sbstudio.plugin.props.frame_range import FrameRangeProperty

from .utils import export_show_to_file_using_api

__all__ = ("SkybrushExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .skyc export operation
#############################################################################


class SkybrushExportOperator(Operator, ExportHelper):
    """Export object trajectories and light animation into the Skybrush compiled format (.skyc)"""

    bl_idname = "export_scene.skybrush"
    bl_label = "Export Skybrush SKYC"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush files
    filter_glob = StringProperty(default="*.skyc", options={"HIDDEN"})
    filename_ext = ".skyc"

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

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        settings = {
            "export_selected": self.export_selected,
            "frame_range": self.frame_range,
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
        }

        if os.path.basename(filepath).lower() == self.filename_ext.lower():
            self.report({"ERROR_INVALID_INPUT"}, "Filename must not be empty")
            return {"CANCELLED"}

        try:
            with call_api_from_blender_operator(self, ".skyc exporter") as api:
                export_show_to_file_using_api(
                    api, context, settings, filepath, FileFormat.SKYC
                )
        except Exception:
            return {"CANCELLED"}

        self.report({"INFO"}, "Export successful")
        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}.skyc"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
