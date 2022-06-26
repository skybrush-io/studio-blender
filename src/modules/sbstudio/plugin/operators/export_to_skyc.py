import bpy
import logging
import os

from bpy.props import BoolProperty, StringProperty, IntProperty
from bpy.types import Context, Operator
from bpy_extras.io_utils import ExportHelper
from natsort import natsorted
from operator import attrgetter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sbstudio.model.color import Color4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.api import get_api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.props import FrameRangeProperty
from sbstudio.plugin.utils import with_context
from sbstudio.plugin.utils.sampling import (
    frame_range,
    sample_colors_of_objects,
    sample_positions_of_objects,
    sample_positions_and_colors_of_objects,
)
from sbstudio.plugin.tasks.light_effects import suspended_light_effects
from sbstudio.plugin.tasks.safety_check import suspended_safety_checks

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
    assert context is not None  # it was injected

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
def _get_trajectories_and_lights(
    drones, settings, bounds: Tuple[int, int], *, context: Optional[Context] = None
) -> Tuple[Dict[str, Trajectory], Dict[str, LightProgram]]:
    """Get trajectories and LED lights of all selected/picked objects.

    Parameters:
        context: the main Blender context
        drones: the list of drones to export
        settings: export settings
        bounds: the frame range used for exporting

    Returns:
        dictionary of Trajectory and LightProgram objects indexed by object names
    """
    trajectory_fps = settings["output_fps"]
    light_fps = settings["light_output_fps"]

    trajectories: Dict[str, Trajectory]
    lights: Dict[str, LightProgram]

    if trajectory_fps == light_fps:
        # This is easy, we can iterate over the show once
        with suspended_safety_checks():
            result = sample_positions_and_colors_of_objects(
                drones,
                frame_range(bounds[0], bounds[1], fps=trajectory_fps, context=context),
                context=context,
                by_name=True,
                simplify=True,
            )

        trajectories = {}
        lights = {}

        for key, (trajectory, light_program) in result.items():
            trajectories[key] = trajectory
            lights[key] = light_program.simplify()

    else:
        # We need to iterate over the show twice, once for the trajectories,
        # once for the lights
        with suspended_safety_checks():
            with suspended_light_effects():
                trajectories = sample_positions_of_objects(
                    drones,
                    frame_range(
                        bounds[0], bounds[1], fps=trajectory_fps, context=context
                    ),
                    context=context,
                    by_name=True,
                    simplify=True,
                )

            lights = sample_colors_of_objects(
                drones,
                frame_range(bounds[0], bounds[1], fps=light_fps, context=context),
                context=context,
                by_name=True,
                simplify=True,
            )

    return trajectories, lights


def _write_skybrush_file(context, settings, filepath: Path) -> None:
    """Creates Skybrush-compatible output from Blender trajectories and color
    animation.

    This is a helper function for SkybrushExportOperator.

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
    log.info("Getting object trajectories and light programs")
    trajectories, lights = _get_trajectories_and_lights(
        drones, settings, frame_range, context=context
    )

    # get automatic show title
    show_title = str(bpy.path.basename(filepath).split(".")[0])

    # get show type
    settings = getattr(context.scene.skybrush, "settings", None)
    show_type = (settings.show_type if settings else "OUTDOOR").lower()

    # get validation parameters
    safety_check = getattr(context.scene.skybrush, "safety_check", None)
    validation = SafetyCheckParams(
        max_velocity_xy=safety_check.velocity_xy_warning_threshold
        if safety_check
        else 8,
        max_velocity_z=safety_check.velocity_z_warning_threshold if safety_check else 2,
        max_altitude=safety_check.max_altitude if safety_check else 150,
        min_distance=safety_check.min_distance if safety_check else 3,
    )

    # create Skybrush converter object
    log.info("Exporting to .skyc")
    get_api().export_to_skyc(
        show_title=show_title,
        show_type=show_type,
        validation=validation,
        trajectories=trajectories,
        lights=lights,
        output=filepath,
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

        _write_skybrush_file(context, settings, filepath)

        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            filepath = bpy.data.filepath or "Untitled"
            filepath, _ = os.path.splitext(filepath)
            self.filepath = f"{filepath}.skyc"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
