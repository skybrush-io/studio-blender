"""Blender addon that exports drone show trajectories and light animation to
a simple (zipped) .csv format compatible with the Skybrush Suite.

The primary and recommended drone show format of the Skybrush Suite is the
Skybrush Compiled Format (.skyc), which is much more versatile and optimized
than the simple text output generated by this script.

This script is created for those who have not started to use our drone show
designer framework, Skybrush Studio Plugin for Blender (yet) or want to use
their own scripts for design but need a Skybrush-compatible output.

To convert this (zipped) .csv to .skyc, login at our site and use
the online converter:

    https://account.skybrush.io

"""

bl_info = {
    "name": "Export Skybrush-compatible CSV Format (.zip)",
    "author": "CollMot Robotics Ltd.",
    "description": "Export object trajectories and color animation to a Skybrush-compatible simple CSV format",
    "version": (1, 0, 0),
    "blender": (2, 83, 0),
    "location": "File > Export > Skybrush-CSV",
    "category": "Import-Export",
}


#############################################################################
# imports needed by the addon

import bpy
import logging
import sys

from bpy.props import BoolProperty, StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from dataclasses import dataclass
from fnmatch import fnmatch
from math import inf, isinf
from operator import attrgetter
from pathlib import Path
from typing import Dict, List, Tuple
from zipfile import ZipFile, ZIP_DEFLATED

#############################################################################
# some global variables that could be parametrized if needed

SUPPORTED_TYPES = ("MESH",)  # ,'CURVE','EMPTY','TEXT','CAMERA','LAMP')


#############################################################################
# configure logger

log = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)


#############################################################################
# Helper functions for the exporter
#############################################################################


@dataclass
class TimePosColor:
    # time in milliseconds
    t: int
    # x position in meters
    x: float
    # y position in meters
    y: float
    # z position in meters
    z: float
    # red channel value [0-255]
    R: int
    # green channel value [0-255]
    G: int
    # blue channel value [0-255]
    B: int

    def __repr__(self):
        return f"{self.t},{round(self.x, ndigits=2)},{round(self.y, ndigits=2)},{round(self.z, ndigits=2)},{self.R},{self.G},{self.B}"


def _to_int_255(value: float) -> int:
    """Convert [0,1] float to clamped [0,255] int."""
    return max(0, min(255, round(value * 255)))


def _get_objects(context, settings):
    """Return generator for objects to export.

    Parameters:
        context - the main Blender context
        settings - export settings

    Yields:
        objects passing all specified filters natural-sorted by their name

    """
    for obj in sorted(context.scene.objects, key=attrgetter("name")):
        if (
            obj.visible_get()
            and obj.type in SUPPORTED_TYPES
            and (
                not settings["export_name_filter"]
                or fnmatch(obj.name, settings["export_name_filter"])
            )
            and (obj.select_get() if settings["export_selected"] else 1)
        ):
            yield obj


def _get_location(obj):
    """Return global location of an object at the actual frame.

    Parameters:
        obj - a Blender object

    Return:
        location of object in the world frame

    """
    return tuple(obj.matrix_world.translation)


def _get_color(obj):
    """Return diffuse_color of an object at the actual frame.

    Parameters:
        obj - a Blender object

    Return:
        color of object as an R, G, B tuple in [0-255]

    """
    if not obj.active_material or not obj.active_material.diffuse_color:
        return (0, 0, 0)

    return (
        _to_int_255(obj.active_material.diffuse_color[0]),
        _to_int_255(obj.active_material.diffuse_color[1]),
        _to_int_255(obj.active_material.diffuse_color[2]),
    )


def _get_frame_range_from_export_settings(context, settings):
    """Get framerange and related variables.

    Parameters:
        context - the main Blender context
        settings - export settings

    Return:
        framerange to be used during the export. Framerange is a 3-tuple
        consisting of (first_frame, last_frame, frame_skip_factor)

    """
    # define frame range and other variables
    fps = context.scene.render.fps
    fpsskip = int(fps / settings["output_fps"])
    last_frames = {}
    if settings["frame_range"] == "RENDER":
        frame_range = [context.scene.frame_start, context.scene.frame_end, fpsskip]
    elif settings["frame_range"] == "PREVIEW":
        frame_range = [
            context.scene.frame_preview_start,
            context.scene.frame_preview_end,
            fpsskip,
        ]
    else:
        raise NotImplementedError("Unknown frame range source")

    return frame_range


def _get_trajectories_and_lights(
    context, settings, frame_range: tuple
) -> Dict[str, List[TimePosColor]]:
    """Get trajectories and lights of all selected/picked objects.

    Parameters:
        context - the main Blender context
        settings - export settings
        framerange - the framerange used for exporting

    Return:
        drone show data in lists of TimePosColor entries, in a dictionary, indexed by object names

    """

    # get object trajectories for each needed frame in convenient format
    fps = context.scene.render.fps
    data = {}
    context.scene.frame_set(frame_range[0])
    # initialize trajectories and lights
    for obj in _get_objects(context, settings):
        data[obj.name] = []
    # parse trajectories and lights
    for frame in range(frame_range[0], frame_range[1] + frame_range[2], frame_range[2]):
        log.debug(f"processing frame {frame}")
        context.scene.frame_set(frame)
        for obj in _get_objects(context, settings):
            pos = _get_location(obj)
            color = _get_color(obj)
            data[obj.name].append(TimePosColor(int(frame / fps * 1000), *pos, *color))

    return data


def _export_data_to_zip(data_dict: Dict[str, List[TimePosColor]], filepath: Path):
    """Export data to individual csv files zipped into a common file."""
    # write .csv files in a .zip file
    with ZipFile(filepath, "w", ZIP_DEFLATED) as zip_file:
        for name, data in data_dict.items():
            lines = ["Time_msec,X,Y,Z,R,G,B"] + [
                str(item) for item in data
            ]
            zip_file.writestr(name + ".csv", "\n".join(lines))


def _write_skybrush_file(context, settings, filepath: Path) -> dict:
    """Creates Skybrush-compatible CSV output from blender trajectories and
    color animation.

    This is a helper function for SkybrushExportOperator

    Parameters:
        context: the main Blender context
        settings: export settings
        filepath: the output path where the export should write

    """

    # get framerange
    log.info("Getting frame range from {}".format(settings["frame_range"]))
    frame_range = _get_frame_range_from_export_settings(context, settings)
    # get trajectories and lights
    log.info("Getting object trajectories and lights")
    trajectories_and_lights = _get_trajectories_and_lights(
        context, settings, frame_range
    )
    # export data to a .zip file containing .csv files
    log.info(f"Exporting object trajectories and light animation to {filepath}")
    _export_data_to_zip(trajectories_and_lights, filepath)

    log.info("Export finished")


#############################################################################
# Operator that allows the user to invoke the export operation
#############################################################################


class SkybrushCSVExportOperator(Operator, ExportHelper):
    """Export object trajectories and light animation into Skybrush-compatible simple CSV format."""

    bl_idname = "export_scene.skybrush_csv"
    bl_label = "Export Skybrush CSV"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush CSV files (zipped)
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    # export objects with the given name filter
    export_name_filter = StringProperty(
        name="Object name filter",
        default="drone_*",
        description="Define a name filter on the objects to be exported. Use the `*` wildcard for convenience.",
    )

    # output all objects or only selected ones
    export_selected = BoolProperty(
        name="Export selected objects only",
        default=True,
        description=(
            "Export only the selected objects from the scene. Uncheck to export "
            "all objects, irrespectively of the selection."
        ),
    )

    # frame range
    frame_range = EnumProperty(
        name="Frame range",
        description="Choose a frame range to use for export",
        items=(
            ("RENDER", "Render", "Use global render frame range set by scene"),
            ("PREVIEW", "Preview", "Use global preview frame range set by scene"),
        ),
        default="RENDER",
    )

    # output frame rate
    output_fps = FloatProperty(
        name="Frame rate",
        default=4,
        description="Temporal resolution of exported trajectory and light (frames per second)",
    )

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        settings = {
            "export_name_filter": self.export_name_filter,
            "export_selected": self.export_selected,
            "frame_range": self.frame_range,
            "output_fps": self.output_fps,
        }

        _write_skybrush_file(context, settings, filepath)

        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


#############################################################################
# Boilerplate to register this as an item in the File / Export menu
#############################################################################


def menu_func_export(self, context):
    self.layout.operator(
        SkybrushCSVExportOperator.bl_idname, text="Skybrush-CSV (.zip)"
    )


def register():
    bpy.utils.register_class(SkybrushCSVExportOperator)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(SkybrushCSVExportOperator)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.object.SkybrushCSVExportOperator("INVOKE_DEFAULT")
