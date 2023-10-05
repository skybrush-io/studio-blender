import bpy
import os

from bpy.props import BoolProperty, StringProperty, FloatProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from sbstudio.model.file_formats import FileFormat
from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.plugin.props.frame_range import FrameRangeProperty

from .base import ExportOperator
from .utils import export_show_to_file_using_api

__all__ = ("DrotekExportOperator",)


#############################################################################
# Operator that allows the user to invoke the Drotek export operation
#############################################################################


class DrotekExportOperator(ExportOperator):
    """Export object trajectories and light animation into Drotek's JSON-based format"""

    bl_idname = "export_scene.drotek"
    bl_label = "Export Drotek format"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Drotek files
    filter_glob = StringProperty(default="*.json", options={"HIDDEN"})
    filename_ext = ".json"

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

    def get_format(self) -> FileFormat:
        """Returns the file format that the operator uses. Must be overridden
        in subclasses.
        """
        return FileFormat.DROTEK

    def get_operator_name(self) -> str:
        return "Drotek exporter"

    def get_settings(self):
        return {
            "spacing": self.spacing,
            "output_fps": 5,
            "light_fps": 5,
            "use_rgbw": self.use_rgbw,
        }
