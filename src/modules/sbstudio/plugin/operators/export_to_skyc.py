import bpy
import logging
import os

from bpy.props import BoolProperty, StringProperty, FloatProperty
from bpy.types import Context, Operator
from bpy_extras.io_utils import ExportHelper
from natsort import natsorted
from operator import attrgetter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sbstudio.model.color import Color4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.api import api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.materials import (
    get_shader_node_and_input_for_diffuse_color_of_material,
)
from sbstudio.plugin.props import FrameRangeProperty
from sbstudio.plugin.utils import with_context
from sbstudio.plugin.utils.sampling import sample_positions_of_objects_in_frame_range

__all__ = ("SkybrushExportOperator", "get_drones_to_export", "resolve_frame_range")

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the exporter
#############################################################################


def _to_int_255(value: float) -> int:
    """Convert [0, 1] float to clamped [0, 255] int."""
    return max(0, min(255, round(value * 255)))


def _create_light_program_from_light_data(
    light_samples: Tuple[List[int], List[float], List[float], List[float]]
) -> LightProgram:
    """Creates a LightProgram object from light data.

    Parameters:
        light: tuple or list of four lists; the first list is the list of frames,
            the remaining three are the R-G-B samples. Values are expected to be
            between [0-1].

    Returns:
        LightProgram object that can be processed by the local Skybrush converter
    """
    samples = [
        Color4D(
            sample[0],
            _to_int_255(sample[1]),
            _to_int_255(sample[2]),
            _to_int_255(sample[3]),
            is_fade=True,
        )
        for sample in zip(*light_samples)
    ]
    return LightProgram(samples).simplify()


def get_drones_to_export(selected_only: bool = False):
    """Returns the drone objects to export.

    Parameters:
        selected_only: whether to export the selected drones only (`True`) or
            all the drones in the appropriate collection (`False`)

    Yields:
        drone objects passing all specified filters natural-sorted by their name
    """
    drone_collection = Collections.find_drones(create=False)
    if not drone_collection:
        return []

    to_export = [
        drone
        for drone in drone_collection.objects
        if not selected_only or drone.select_get()
    ]

    return natsorted(to_export, key=attrgetter("name"))


@with_context
def resolve_frame_range(
    range: str, *, context: Optional[Context] = None
) -> Tuple[int, int]:
    """Resolves one of the commonly used frame ranges used in multiple places
    throughout the plugin.
    """
    if range == "RENDER":
        # Return the entire frame range of the current scene
        return (context.scene.frame_start, context.scene.frame_end)
    elif range == "PREVIEW":
        # Return the selected preview range of the current scene
        return (context.scene.frame_preview_start, context.scene.frame_preview_end)
    elif range == "STORYBOARD":
        # Return the frame range covered by the storyboard
        return (
            context.scene.skybrush.storyboard.frame_start,
            context.scene.skybrush.storyboard.frame_end,
        )
    else:
        raise RuntimeError(f"Unknown frame range: {range!r}")


@with_context
def _get_frame_range_from_export_settings(
    settings, *, context: Optional[Context] = None
) -> Tuple[int, int]:
    """Returns the range of frames to export, based on the chosen export settings
    of the user.

    Parameters:
        settings: the export settings chosen by the user
        context: the main Blender context

    Returns:
        frame range to be used during the export (both ends inclusive)
    """
    return resolve_frame_range(settings["frame_range"], context=context)


@with_context
def _get_trajectories(
    drones, settings, frame_range: Tuple[int, int], *, context: Optional[Context] = None
) -> Dict[str, Trajectory]:
    """Get trajectories of all selected/picked objects.

    Parameters:
        context: the main Blender context
        drones: the list of drones to export
        settings: export settings
        frame_range: the frame range used for exporting

    Returns:
        dictionary of Trajectory objects indexed by object names
    """
    return sample_positions_of_objects_in_frame_range(
        drones, frame_range, fps=settings["output_fps"], context=context, by_name=True
    )


@with_context
def _get_lights(
    drones, settings, frame_range: Tuple[int, int], *, context: Optional[Context] = None
) -> Dict[str, LightProgram]:
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

    frames = list(range(frame_range[0], frame_range[1] + 1))
    ts = [frame / fps for frame in frames]

    for drone in drones:
        name = drone.name
        log.debug(f"processing {name}")

        # if there is no material associated with the object, we use const black
        material = drone.active_material
        if not material:
            light_dict[name] = [
                ts,
                [0] * num_frames,
                [0] * num_frames,
                [0] * num_frames,
            ]
            continue

        # if color is not animated, use a single color
        animation = material.node_tree.animation_data
        if not animation:
            light_dict[name] = [ts] + [
                [x] * num_frames for x in material.diffuse_color[:3]
            ]
            continue

        # if color is animated, sample it on all frames first
        light_dict[name] = [None] * 4
        light_dict[name][0] = ts
        node, input = get_shader_node_and_input_for_diffuse_color_of_material(material)
        index = node.inputs.find(input.name)
        data_path = f'nodes["{node.name}"].inputs[{index}].default_value'

        for fc in animation.action.fcurves:
            if fc.data_path != data_path:
                continue

            # iterate channels (r, g, b) only
            if fc.array_index not in (0, 1, 2):
                continue

            light_dict[name][fc.array_index + 1] = [
                fc.evaluate(frame) for frame in frames
            ]

    # convert to skybrush-compatible format (and simplify)
    lights = dict(
        (name, _create_light_program_from_light_data(light))
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
    log.info("Getting frame range from {}".format(settings["frame_range"]))
    frame_range = _get_frame_range_from_export_settings(settings, context=context)

    # determine list of drones to export
    drones = list(get_drones_to_export(settings["export_selected"]))

    # get trajectories
    log.info("Getting object trajectories")
    trajectories = _get_trajectories(drones, settings, frame_range, context=context)

    # get lights
    log.info("Getting object color animations")
    lights = _get_lights(drones, settings, frame_range, context=context)

    # get automatic show title
    show_title = "Show '{}' exported from Blender".format(
        bpy.path.basename(filepath).split(".")[0]
    )

    # create Skybrush converter object
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
            "Export only the selected drones. "
            "Uncheck to export all drones, irrespectively of the selection."
        ),
    )

    # frame range
    frame_range = FrameRangeProperty()

    # output frame rate
    output_fps = FloatProperty(
        name="Frame rate",
        default=4,
        description="Temporal resolution of exported trajectory (frames per second)",
    )

    def execute(self, context):
        filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        settings = {
            "export_selected": self.export_selected,
            "frame_range": self.frame_range,
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
