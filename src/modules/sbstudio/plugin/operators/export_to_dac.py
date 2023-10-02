import bpy
import os

from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from sbstudio.model.file_formats import FileFormat
from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.plugin.props.frame_range import FrameRangeProperty

from .utils import export_show_to_file_using_api

__all__ = ("DACExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .dac export operation
#############################################################################


class DACExportOperator(Operator, ExportHelper):
    """Export object trajectories and light animation into .dac format."""

    bl_idname = "export_scene.dac"
    bl_label = "Export DAC"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to .dac files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

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

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        settings = {
            "export_selected": self.export_selected,
            "frame_range": self.frame_range,
            "output_fps": 30,
            "light_output_fps": 30,
        }

        try:
            with call_api_from_blender_operator(self, ".dac exporter") as api:
                export_show_to_file_using_api(
                    api, context, settings, filepath, FileFormat.DAC
                )
        except Exception:
            return {"CANCELLED"}

        self.report({"INFO"}, "Export successful")
        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}.zip"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
