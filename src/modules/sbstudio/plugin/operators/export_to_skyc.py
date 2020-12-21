import bpy
import logging
import os

from bpy.props import BoolProperty, StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from natsort import natsorted
from operator import attrgetter
from pathlib import Path
from typing import Dict, List

from sbstudio.model.color import Color4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.point import Point4D
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.api import api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.materials import (
    get_shader_node_and_input_for_diffuse_color_of_material,
)

__all__ = ("SkybrushExportOperator",)

log = logging.getLogger(__name__)

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


def _get_drones(context, settings):
    """Return drone objects to export.

    Parameters:
        context - the main Blender context
        settings - export settings

    Yields:
        drone objects passing all specified filters natural-sorted by their name

    """
    drone_collection = Collections.find_drones(create=False)
    if not drone_collection:
        return []

    to_export = [
        drone
        for drone in drone_collection.objects
        if not settings["export_selected"] or drone.select_get()
    ]

    return natsorted(to_export, key=attrgetter("name"))


def _get_location(object):
    """Return global location of an object at the actual frame.

    Parameters:
        object - a Blender object

    Return:
        location of object in the world frame

    """
    return tuple(object.matrix_world.translation)


def _get_framerange(context, settings):
    """Get framerange based on user settings.

    Parameters:
        context - the main Blender context
        settings - export settings

    Return:
        (first_frame, last_frame) framerange to be used during the export

    """
    # define frame range and other variables
    if settings["frame_range_source"] == "RENDER":
        return (context.scene.frame_start, context.scene.frame_end)
    elif settings["frame_range_source"] == "PREVIEW":
        return (context.scene.frame_preview_start, context.scene.frame_preview_end)
    elif settings["frame_range_source"] == "STORYBOARD":
        return (
            context.scene.skybrush.storyboard.frame_start,
            context.scene.skybrush.storyboard.frame_end,
        )
    else:
        raise NotImplementedError("Unknown frame range source")


def _get_trajectories(context, settings, frame_range: tuple) -> Dict[str, Trajectory]:
    """Get trajectories of all selected/picked objects.

    Parameters:
        context - the main Blender context
        settings - export settings
        framerange - the framerange used for exporting

    Return:
        dictionary of Trajectory objects indexed by object names

    """

    # initialize trajectories
    fps = context.scene.render.fps
    drones = _get_drones(context, settings)
    trajectories = dict((drone.name, Trajectory()) for drone in drones)
    # parse trajectories
    frame_step = max(1, int(fps / settings["output_fps"]))
    context.scene.frame_set(frame_range[0])
    for frame in range(frame_range[0], frame_range[1] + frame_step, frame_step):
        log.debug(f"processing frame {frame}")
        context.scene.frame_set(frame)
        for drone in drones:
            trajectories[drone.name].append(Point4D(frame / fps, *_get_location(drone)))

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
    for drone in _get_drones(context, settings):
        name = drone.name
        log.debug(f"processing {name}")
        # if there is no material associated with the object, we use const black
        if not drone.active_material:
            light_dict[name] = [[0] * num_frames, [0] * num_frames, [0] * num_frames]
            continue
        material = drone.active_material
        # if color is not animated, use a single color
        if not material.node_tree.animation_data:
            light_dict[name] = [[x] * num_frames for x in material.diffuse_color[:3]]
            continue
        animation = material.node_tree.animation_data
        # if color is animated, sample it on all frames first
        light_dict[name] = [[], [], []]
        node, input = get_shader_node_and_input_for_diffuse_color_of_material(material)
        index = node.inputs.find(input.name)
        data_path = f'nodes["{node.name}"].inputs[{index}].default_value'
        for fc in animation.action.fcurves:
            if fc.data_path != data_path:
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
    log.info("Exporting to .skyc")
    api.export_to_skyc(
        show_title=show_title, trajectories=trajectories, lights=lights, output=filepath
    )
    log.info("Export finished")


#############################################################################
# Operator that allows the user to invoke the export operation
#############################################################################


class SkybrushExportOperator(Operator, ExportHelper):
    """Export object trajectories and curves into Skybrush-compatible format."""

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
            "Export only the selected objects from the Drones Collection. "
            "Uncheck to export all drones, irrespectively of the selection."
        ),
    )

    # frame range source
    frame_range_source = EnumProperty(
        name="Frame range source",
        description="Choose a frame range source to use for export",
        items=(
            ("STORYBOARD", "Storyboard", "Use the storyboard to define frame range"),
            ("RENDER", "Render", "Use global render frame range set by scene"),
            ("PREVIEW", "Preview", "Use global preview frame range set by scene"),
        ),
        default="STORYBOARD",
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
        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}.skyc"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
