import bpy
import os

from bpy.props import BoolProperty, StringProperty, FloatProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from sbstudio.model.file_formats import FileFormat
from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.plugin.props.frame_range import FrameRangeProperty

from .utils import export_show_to_file_using_api

__all__ = ("DrotekExportOperator",)


#############################################################################
# Operator that allows the user to invoke the Drotek export operation
#############################################################################


class DrotekExportOperator(Operator, ExportHelper):
    """Export object trajectories and light animation into Drotek's JSON-based format"""

    bl_idname = "export_scene.drotek"
    bl_label = "Export Drotek format"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Drotek files
    filter_glob = StringProperty(default="*.json", options={"HIDDEN"})
    filename_ext = ".json"

    # output all objects or only selected ones
    export_selected = BoolProperty(
        name="Export selected drones only",
        default=False,
        description=(
            "Export only the selected drones. "
            "Uncheck to export all drones, irrespectively of the selection."
        ),
    )

    # whether to convert RGB colors to RGBW during export
    use_rgbw = BoolProperty(
        name="Use RGBW colors",
        default=True,
        description="Whether to convert colors to RGBW automatically during export",
    )

    # spacing between drones in the takeoff grid
    spacing = FloatProperty(
        name="Takeoff grid spacing",
        default=2,
        description="Distance between slots in the takeoff grid.",
    )

    # frame range
    frame_range = FrameRangeProperty(default="RENDER")

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        settings = {
            "export_selected": self.export_selected,
            "frame_range": self.frame_range,
            "spacing": self.spacing,
            "output_fps": 5,
            "light_fps": 5,
            "use_rgbw": self.use_rgbw,
        }

        try:
            with call_api_from_blender_operator(self, "Drotek exporter") as api:
                export_show_to_file_using_api(
                    api,
                    context,
                    settings,
                    filepath,
                    FileFormat.DROTEK,
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
