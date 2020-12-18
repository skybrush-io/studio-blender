"""Blender add-on that allows the user to export drone trajectories and light
animation to Skybrush compiled file format (*.skyc).
"""

bl_info = {
    "name": "Legacy Export Skybrush Compiled Format (.skyc)",
    "author": "Gabor Vasarhelyi (CollMot Robotics Ltd.)",
    "description": "Export object trajectories and color animation to Skybrush compiled format (legacy version)",
    "version": (0, 2, 1),
    "blender": (2, 83, 0),
    "location": "File > Export > Skybrush",
    "category": "Import-Export",
}


#############################################################################
# imports needed to set up the Python path properly

import bpy
import sys

from bpy.path import abspath
from pathlib import Path


#############################################################################
# Note: This code needs to be harmonized with the plugin installer to have
# the same target directory for all add-on specific dependencies.

candidates = [
    abspath(bpy.context.preferences.filepaths.script_directory),
    Path(sys.modules[__name__].__file__).parent.parent,
]
for candidate in candidates:
    path = (Path(candidate) / "vendor" / "skybrush").resolve()
    if path.exists():
        sys.path.insert(0, str(path))
        break


#############################################################################
# imports needed by the addon

import logging

from bpy.props import BoolProperty, StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from fnmatch import fnmatch
from math import isinf
from natsort import natsorted
from operator import attrgetter
from typing import Dict, List

from sbstudio.api.operations.export import SkybrushExporter
from sbstudio.model.color import Color4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.point import Point4D
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.plugin_helpers import (
    register_in_menu,
    register_operator,
    unregister_from_menu,
    unregister_operator,
)


#############################################################################
# some global variables that could be parametrized if needed

SUPPORTED_TYPES = ("MESH",)  # ,'CURVE','EMPTY','TEXT','CAMERA','LAMP')
SUPPORTED_NAMES = "drone_*"


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


def _to_int_255(value: float) -> int:
    """Convert [0,1] float to clamped [0,255] int."""
    return max(0, min(255, round(value * 255)))


def _create_light_program_from_light_data(
    light: List[List], frame_range: List, fps: float
) -> LightProgram:
    """Creates a LightProgram object from light data.

    Parameters:
        light: list of 3 lists, each containing a list of colors for all frames
            for the given frame range. Values are expected to be between [0-1].
        frame_range: frame_start, frame_end, _
        fps: frames per second of the light data

    Return:
        LightProgram object that can be processed by the local Skybrush converter

    """

    samples = [
        Color4D(
            frame / fps,
            _to_int_255(light[0][i]),
            _to_int_255(light[1][i]),
            _to_int_255(light[2][i]),
            is_fade=True,
        )
        for i, frame in enumerate(range(frame_range[0], frame_range[1] + 1))
    ]

    return LightProgram(samples).simplify()


def _get_objects(context, settings):
    """Return generator for objects to export.

    Parameters:
        context - the main Blender context
        settings - export settings

    Yields:
        objects passing all specified filters natural-sorted by their name

    """
    for ob in natsorted(context.scene.objects, key=attrgetter("name")):
        if ob.visible_get() and (
            ob.select_get()
            if settings["export_selected"]
            else (fnmatch(ob.name, SUPPORTED_NAMES) and ob.type in SUPPORTED_TYPES)
        ):
            yield ob


def _get_location(object):
    """Return global location of an object at the actual frame.

    Parameters:
        object - a Blender object

    Return:
        location of object in the world frame

    """
    return tuple(object.matrix_world.translation)


def _get_framerange(context, settings):
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
    if settings["frame_range_source"] == "RENDER":
        frame_range = [context.scene.frame_start, context.scene.frame_end, fpsskip]
    elif settings["frame_range_source"] == "PREVIEW":
        frame_range = [
            context.scene.frame_preview_start,
            context.scene.frame_preview_end,
            fpsskip,
        ]
    elif settings["frame_range_source"] == "LOCAL":
        # get largest common frame_range
        frame_range_min = float("Inf")
        frame_range_max = -float("Inf")
        for obj in _get_objects(context, settings):
            last_frames[obj.name] = -float("Inf")
            # check object's own animation data and its follow_path constraints, too
            follow_path_constraints = [
                cons for cons in obj.constraints if cons.type == "FOLLOW_PATH"
            ]
            targets = [cons.target for cons in follow_path_constraints]
            curves = [target.data for target in targets]
            for curve in curves + [obj]:
                if curve.animation_data:
                    new_frame_range = [
                        int(x) for x in curve.animation_data.action.frame_range
                    ]
                    if new_frame_range[0] < frame_range_min:
                        frame_range_min = new_frame_range[0]
                    if new_frame_range[1] > frame_range_max:
                        frame_range_max = new_frame_range[1]
                    if new_frame_range[1] > last_frames[obj.name]:
                        last_frames[obj.name] = new_frame_range[1]
            if isinf(last_frames[obj.name]):
                raise UnboundLocalError(
                    "There is no local frame range defined for '%s'", obj.name
                )
        if isinf(frame_range_min) or isinf(frame_range_max):
            raise UnboundLocalError(
                "There is no local frame range defined for any of the objects."
            )
        frame_range = [frame_range_min, frame_range_max, fpsskip]
    else:
        raise NotImplementedError("Unknown frame range source")

    return frame_range


def _get_trajectories(context, settings, frame_range: tuple) -> Dict[str, Trajectory]:
    """Get trajectories of all selected/picked objects.

    Parameters:
        context - the main Blender context
        settings - export settings
        framerange - the framerange used for exporting

    Return:
        dictionary of Trajectory objects indexed by object names

    """

    # get object trajectories for each needed frame in convenient format
    fps = context.scene.render.fps
    trajectories = (
        {}
    )  # trajectories[name] = timeline of Point4D(t, x, y, z) positions of object 'name'
    context.scene.frame_set(frame_range[0])
    # initialize trajectories
    for obj in _get_objects(context, settings):
        trajectories[obj.name] = Trajectory()
    # parse trajectories
    for frame in range(frame_range[0], frame_range[1] + frame_range[2], frame_range[2]):
        log.debug(f"processing frame {frame}")
        context.scene.frame_set(frame)
        for obj in _get_objects(context, settings):
            trajectories[obj.name].append(Point4D(frame / fps, *_get_location(obj)))

    return trajectories


def _get_lights(context, settings, frame_range: tuple) -> Dict[str, LightProgram]:
    """Get light animation of all selected/picked objects.

    Parameters:
        context - the main Blender context
        settings - export settings
        framerange - the framerange used for exporting

    Return:
        dictionary of LightProgram objects indexed by object names
    """

    # get object color animations for each frame
    fps = context.scene.render.fps
    num_frames = frame_range[1] - frame_range[0] + 1
    light_dict = {}
    for obj in _get_objects(context, settings):
        name = obj.name
        log.debug(f"processing {name}")
        # if there is no material associated with the object, we use const black
        if not obj.active_material:
            light_dict[name] = [[0] * num_frames, [0] * num_frames, [0] * num_frames]
            continue
        # if color is not animated, use a single color
        if not obj.active_material.animation_data:
            light_dict[name] = [
                [x] * num_frames for x in obj.active_material.diffuse_color[:3]
            ]
            continue
        # if color is animated, sample it on all frames first
        light_dict[name] = [[], [], []]
        for fc in obj.active_material.animation_data.action.fcurves:
            if fc.data_path != "diffuse_color":
                continue
            # iterate channels (r, g, b) only
            if fc.array_index not in (0, 1, 2):
                # TODO: we do not support alpha channel parsing yet
                continue
            light_dict[name][fc.array_index] = [
                fc.evaluate(frame)
                for frame in range(frame_range[0], frame_range[1] + 1)
            ]

    # convert to skybrush-compatible format (and simplify)
    lights = dict(
        (name, _create_light_program_from_light_data(light, frame_range, fps))
        for name, light in light_dict.items()
    )

    return lights


def _write_skybrush_file(context, settings, filepath: Path) -> dict:
    """Creates Skybrush-compatible output from blender trajectories and color
    animation.

    This is a helper function for SkybrushExportOperator

    Parameters:
        context: the main Blender context
        settings: export settings
        filepath: the output path where the export should write

    """

    log.info(f"Exporting show content to {filepath}")

    # get framerange
    log.info("Getting frame range from {}".format(settings["frame_range_source"]))
    frame_range = _get_framerange(context, settings)
    # get trajectories
    log.info("Getting object trajectories")
    trajectories = _get_trajectories(context, settings, frame_range)
    # get lights
    log.info("Getting object color animations")
    lights = _get_lights(context, settings, frame_range)

    # get automatic show title
    show_title = "Show '{}' exported from Blender".format(
        bpy.path.basename(filepath).split(".")[0]
    )

    # create skybrush converter object
    log.info("Creating exporter object")
    converter = SkybrushExporter(
        show_title=show_title, trajectories=trajectories, lights=lights
    )

    # export to .skyc
    log.info("Exporting to .skyc")
    converter.to_skyc(filepath)

    log.info("Export finished")


#############################################################################
# Operator that allows the user to invoke the export operation
#############################################################################


class SkybrushExportOperator(Operator, ExportHelper):
    """Legacy Export object trajectories and curves into Skybrush-compatible format."""

    bl_idname = "legacy_export_scene.skybrush"
    bl_label = "Legacy Export Skybrush SKYC"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush files
    filter_glob = StringProperty(default="*.skyc", options={"HIDDEN"})
    filename_ext = ".skyc"

    # output all objects or only selected ones
    export_selected = BoolProperty(
        name="Export selected objects only",
        default=True,
        description=(
            "Export only the selected drones from the scene. Uncheck to export "
            "all drones, irrespectively of the selection."
        ),
    )

    # frame range source
    frame_range_source = EnumProperty(
        name="Frame range source",
        description="Choose a frame range source to use for export",
        items=(
            ("LOCAL", "Local", "Use local frame range stored in animation data"),
            ("RENDER", "Render", "Use global render frame range set by scene"),
            ("PREVIEW", "Preview", "Use global preview frame range set by scene"),
        ),
        default="LOCAL",
    )

    # output frame rate
    output_fps = FloatProperty(
        name="Frame rate",
        default=1,
        description="Temporal resolution of exported trajectory (frames per second)",
    )

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        settings = {
            "export_selected": self.export_selected,
            "frame_range_source": self.frame_range_source,
            "output_fps": self.output_fps,
        }

        _write_skybrush_file(context, settings, filepath)

        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


#############################################################################
# Boilerplate to register this as an item in the File / Import menu
#############################################################################


def menu_func_export(self, context):
    self.layout.operator(
        SkybrushExportOperator.bl_idname, text="Legacy Skybrush (.skyc)"
    )


def register():
    register_operator(SkybrushExportOperator)
    register_in_menu("File / Export", menu_func_export)


def unregister():
    unregister_operator(SkybrushExportOperator)
    unregister_from_menu("File / Export", menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.object.SkybrushExportOperator("INVOKE_DEFAULT")
