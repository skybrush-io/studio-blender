from typing import Any

from bpy.props import EnumProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("DACExportOperator",)


#############################################################################
# Operator that allows the user to invoke the .dac export operation
#############################################################################


class DACExportOperator(ExportOperator):
    """Export object trajectories and light animation into .dac format."""

    bl_idname = "export_scene.dac"
    bl_label = "Export DAC"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to .dac files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    drone_model = EnumProperty(
        name="Drone model",
        description="List of supported High Great drone models",
        items=[
            ("FYLO", "Fylo", "High Great Fylo indoor drone"),
            ("EMO", "Emo", "High Great EMO outdoor drone"),
        ],
        default="FYLO",
    )

    gcs_type = EnumProperty(
        name="GCS type",
        description="List of GCS software used with High Great drone models",
        items=[
            ("BEEDANCE", "Beedance", "BeeDance - for indoor Fylo drones"),
            ("FLYDANCE", "Flydance", "FlyDance - for outdoor EMO drones"),
            ("ZEROSPACE", "Zerospace", "ZeroSpace - for outdoor EMO drones"),
        ],
        default="BEEDANCE",
    )

    def get_format(self) -> FileFormat:
        return FileFormat.DAC

    def get_operator_name(self) -> str:
        return ".dac exporter"

    def get_settings(self) -> dict[str, Any]:
        return {
            "output_fps": 30,
            "light_output_fps": 30,
            "drone_model": self.drone_model.lower(),
            "gcs_type": self.gcs_type.lower(),
        }
