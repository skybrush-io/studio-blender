"""Utility functions for operators."""

import logging

from bpy.path import basename
from bpy.types import Context

from contextlib import contextmanager
from itertools import groupby
from math import degrees
from natsort import natsorted
from operator import attrgetter
from pathlib import Path
from typing import Any, Iterator, Optional, cast

from sbstudio.api import SkybrushStudioAPI
from sbstudio.model.file_formats import FileFormat
from sbstudio.model.light_program import LightProgram
from sbstudio.model.location import ShowLocation
from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.model.trajectory import Trajectory
from sbstudio.model.yaw import YawSetpointList
from sbstudio.plugin.model.storyboard import (
    StoryboardEntry,
    StoryboardEntryPurpose,
    get_storyboard,
)
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.errors import SkybrushStudioExportWarning, TaskCancelled
from sbstudio.plugin.gateway import get_gateway
from sbstudio.plugin.props.frame_range import resolve_frame_range
from sbstudio.plugin.tasks.light_effects import suspended_light_effects
from sbstudio.plugin.tasks.safety_check import suspended_safety_checks
from sbstudio.plugin.utils import with_context
from sbstudio.plugin.utils.cameras import get_cameras_from_context
from sbstudio.plugin.utils.gps_coordinates import parse_latitude, parse_longitude
from sbstudio.plugin.utils.progress import ProgressHandler, ProgressReport
from sbstudio.plugin.utils.pyro_markers import get_pyro_markers_of_object
from sbstudio.plugin.utils.sampling import (
    frame_range,
    sample_colors_of_objects,
    sample_positions_of_objects,
    sample_positions_and_colors_of_objects,
    sample_positions_and_yaw_of_objects,
    sample_positions_colors_and_yaw_of_objects,
)
from sbstudio.plugin.utils.time_markers import get_time_markers_from_context
from sbstudio.utils import get_ends

__all__ = (
    "get_drones_to_export",
    "export_show_to_file_using_api",
)


log = logging.getLogger(__name__)


class _default_settings:
    output_fps: int = 4
    light_output_fps: int = 4
    redraw: Optional[bool] = None


################################################################################
# Helper functions for exporter operators


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
def _get_frame_range_from_export_settings(
    settings, *, context: Optional[Context] = None
) -> Optional[tuple[int, int]]:
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
def _get_segments(context: Optional[Context] = None) -> dict[str, tuple[float, float]]:
    """Returns dictionary that maps show segment IDs to start (inclusive) and
    end (exclusive) timestamps.

    If invalid configuration is found for a segment, then the segment will be omitted
    from the result.
    """
    result: dict[str, tuple[float, float]] = {}
    storyboard = get_storyboard(context=context)
    fps = context.scene.render.fps

    entry_purpose_groups = groupby(storyboard.entries, lambda e: cast(str, e.purpose))

    takeoff_entries: list[StoryboardEntry] | None = None
    show_entries: list[StoryboardEntry] | None = None
    landing_entries: list[StoryboardEntry] | None = None
    show_valid = True
    for purpose, entries in entry_purpose_groups:
        if purpose == StoryboardEntryPurpose.UNSPECIFIED.name:
            show_valid = False
            break
        elif purpose == StoryboardEntryPurpose.TAKEOFF.name:
            if not (show_entries is None and landing_entries is None):
                show_valid = False
                break

            takeoff_entries = list(entries)
        elif purpose == StoryboardEntryPurpose.SHOW.name:
            if landing_entries is not None:
                show_valid = False
                break

            show_entries = list(entries)
        elif purpose == StoryboardEntryPurpose.LANDING.name:
            landing_entries = list(entries)

    if show_valid:
        if ends := get_ends(takeoff_entries):
            result["takeoff"] = (ends[0].frame_start / fps, ends[1].frame_end / fps)
        if ends := get_ends(show_entries):
            result["show"] = (ends[0].frame_start / fps, ends[1].frame_end / fps)
        if ends := get_ends(landing_entries):
            result["landing"] = (ends[0].frame_start / fps, ends[1].frame_end / fps)
    elif (
        takeoff_entries is not None
        or show_entries is not None
        or landing_entries is not None
    ):
        log.warning("Show segments are invalid!")

    return result


@with_context
def _get_trajectories_and_lights(
    drones,
    settings: dict[str, Any],
    bounds: tuple[int, int],
    *,
    context: Context | None = None,
    progress: ProgressHandler | None = None,
) -> tuple[dict[str, Trajectory], dict[str, LightProgram]]:
    """Get trajectories and LED lights of all selected/picked objects.

    Parameters:
        context: the main Blender context
        drones: the list of drones to export
        settings: export settings
        bounds: the frame range used for exporting

    Returns:
        dictionary of Trajectory and LightProgram objects indexed by object names
    """
    trajectory_fps = settings.get("output_fps", _default_settings.output_fps)
    light_fps = settings.get("light_output_fps", _default_settings.light_output_fps)
    redraw = settings.get("redraw", _default_settings.redraw)

    if redraw is None:
        # Redraw the scene if we have at least one video-based light effect but
        # do not redraw otherwise
        assert context is not None
        redraw = any(
            effect.is_animated
            for effect in context.scene.skybrush.light_effects.entries
        )

    frames = frame_range(
        bounds[0],
        bounds[1],
        context=context,
    )

    trajectories: dict[str, Trajectory]
    lights: dict[str, LightProgram]

    if trajectory_fps == light_fps:
        # This is easy, we can iterate over the show once
        with suspended_safety_checks():
            frame_iter = frames.iter(
                trajectory_fps,
                operation="Sampling trajectories and lights",
                on_progress=progress,
            )
            result = sample_positions_and_colors_of_objects(
                drones,
                frame_iter,
                context=context,
                redraw=redraw,
                simplify=True,
            )

        trajectories = {}
        lights = {}

        for key, (trajectory, light_program) in result.items():
            trajectories[key] = trajectory
            lights[key] = light_program

    else:
        # We need to iterate over the show twice, once for the trajectories,
        # once for the lights
        with suspended_safety_checks():
            frame_iter = frames.iter(
                trajectory_fps,
                operation="Sampling trajectories",
                on_progress=progress,
            )
            with suspended_light_effects():
                trajectories = sample_positions_of_objects(
                    drones,
                    frame_iter,
                    context=context,
                    simplify=True,
                )

            frame_iter = frames.iter(
                light_fps,
                operation="Sampling lights",
                on_progress=progress,
            )
            lights = sample_colors_of_objects(
                drones,
                frame_iter,
                context=context,
                redraw=redraw,
                simplify=True,
            )

    return trajectories, lights


@with_context
def _get_trajectories_lights_and_yaw_setpoints(
    drones,
    settings: dict[str, Any],
    bounds: tuple[int, int],
    *,
    context: Context | None = None,
    progress: ProgressHandler | None = None,
) -> tuple[dict[str, Trajectory], dict[str, LightProgram], dict[str, YawSetpointList]]:
    """Get trajectories, LED lights and yaw setpoints of all selected/picked objects.

    Parameters:
        context: the main Blender context
        drones: the list of drones to export
        settings: export settings
        bounds: the frame range used for exporting

    Returns:
        dictionary of Trajectory, LightProgram and YawSetpointList objects indexed by object names
    """
    trajectory_fps = settings.get("output_fps", _default_settings.output_fps)
    light_fps = settings.get("light_output_fps", _default_settings.light_output_fps)
    redraw = settings.get("redraw", _default_settings.redraw)

    if redraw is None:
        # Redraw the scene if we have at least one video-based light effect but
        # do not redraw otherwise
        assert context is not None
        redraw = any(
            effect.is_animated
            for effect in context.scene.skybrush.light_effects.entries
        )

    frames = frame_range(
        bounds[0],
        bounds[1],
        context=context,
    )

    trajectories: dict[str, Trajectory]
    lights: dict[str, LightProgram]
    yaw_setpoints: dict[str, YawSetpointList]

    if trajectory_fps == light_fps:
        # This is easy, we can iterate over the show once
        with suspended_safety_checks():
            frame_iter = frames.iter(
                trajectory_fps,
                operation="Sampling trajectories, lights and yaw setpoints",
                on_progress=progress,
            )
            result = sample_positions_colors_and_yaw_of_objects(
                drones,
                frame_iter,
                context=context,
                redraw=redraw,
                simplify=True,
            )

        trajectories = {}
        lights = {}
        yaw_setpoints = {}

        for key, (trajectory, light_program, yaw_curve) in result.items():
            trajectories[key] = trajectory
            lights[key] = light_program
            yaw_setpoints[key] = yaw_curve

    else:
        # We need to iterate over the show twice, once for the trajectories
        # and yaw setpoints, once for the lights
        with suspended_safety_checks():
            frame_iter = frames.iter(
                trajectory_fps,
                operation="Sampling trajectories and yaw setpoints",
                on_progress=progress,
            )
            with suspended_light_effects():
                result = sample_positions_and_yaw_of_objects(
                    drones,
                    frame_iter,
                    context=context,
                    simplify=True,
                )

                trajectories = {}
                yaw_setpoints = {}

                for key, (trajectory, yaw_curve) in result.items():
                    trajectories[key] = trajectory
                    yaw_setpoints[key] = yaw_curve

            frame_iter = frames.iter(
                light_fps,
                operation="Sampling lights",
                on_progress=progress,
            )
            lights = sample_colors_of_objects(
                drones,
                frame_iter,
                context=context,
                redraw=redraw,
                simplify=True,
            )

    return trajectories, lights, yaw_setpoints


@contextmanager
def _report_progress_on_console(title: str = "") -> Iterator[ProgressHandler]:
    def reporter(progress: ProgressReport) -> bool:
        print(progress.format())
        return False

    if title:
        print(f"{title}...")

    failed = False

    try:
        yield reporter
    except (KeyboardInterrupt, TaskCancelled):
        print("Operation cancelled by user.")
        failed = True
    except Exception as ex:
        print(f"Operation failed: {ex}")
        failed = True
    finally:
        print(f"{title}: {'failed' if failed else 'done'}.")


@contextmanager
def report_progress_during_api_operation(title: str = "") -> Iterator[ProgressHandler]:
    try:
        gateway = get_gateway()
    except Exception:
        gateway = None

    ctx = (
        gateway.use_new_operation(title=title)
        if gateway
        else _report_progress_on_console(title)
    )
    with ctx as on_progress:
        yield on_progress


def export_show_to_file_using_api(
    api: SkybrushStudioAPI,
    context: Context,
    settings: dict[str, Any],
    filepath: Path,
    format: FileFormat,
) -> None:
    """Creates Skybrush-compatible output from Blender trajectories and color
    animation.

    This is a helper function for Skybrush export operators.

    Parameters:
        api: the Skybrush Studio API object
        context: the main Blender context
        settings: export settings dictionary
        filepath: the output path where the export should write
        format: the format that the API should produce

    Raises:
        SkybrushStudioExportWarning: when a local check failed and the export
            operation did not start. These are converted into warnings on the
            Blender UI.
        SkybrushStudioAPIError: for server-side export errors. These are
            converted into errors on the Blender UI.
    """

    log.info(f"Exporting show content to {filepath}")

    # get framerange
    log.info(f"Getting frame range from {settings.get('frame_range')}")
    frame_range = _get_frame_range_from_export_settings(settings, context=context)
    if frame_range is None:
        raise SkybrushStudioExportWarning("Selected frame range is empty")

    # determine list of drones to export
    export_selected_only: bool = settings.get("export_selected", False)
    drones = list(get_drones_to_export(selected_only=export_selected_only))
    if not drones:
        if export_selected_only:
            raise SkybrushStudioExportWarning(
                "No objects were selected; export cancelled"
            )
        else:
            raise SkybrushStudioExportWarning(
                "There are no objects to export; export cancelled"
            )

    # get yaw control enabled state
    use_yaw_control: bool = settings.get("use_yaw_control", False)

    # get trajectories, light programs and yaw setpoints
    with report_progress_during_api_operation() as on_progress:
        if use_yaw_control:
            log.info("Getting object trajectories, light programs and yaw setpoints")
            (
                trajectories,
                lights,
                yaw_setpoints,
            ) = _get_trajectories_lights_and_yaw_setpoints(
                drones,
                settings,
                frame_range,
                context=context,
                progress=on_progress,
            )
        else:
            log.info("Getting object trajectories and light programs")
            (
                trajectories,
                lights,
            ) = _get_trajectories_and_lights(
                drones,
                settings,
                frame_range,
                context=context,
                progress=on_progress,
            )
            yaw_setpoints = None

    # get pyro control enabled state
    use_pyro_control: bool = settings.get("use_pyro_control", False)

    if use_pyro_control:
        pyro_programs = {
            drone.name: get_pyro_markers_of_object(drone) for drone in drones
        }
    else:
        pyro_programs = None

    # get automatic show title
    show_title = str(basename(filepath).split(".")[0])

    # get show type and location
    scene_settings = getattr(context.scene.skybrush, "settings", None)
    show_type = (scene_settings.show_type if scene_settings else "OUTDOOR").lower()
    show_location = (
        ShowLocation(
            latitude=parse_latitude(scene_settings.latitude_of_show_origin),
            longitude=parse_longitude(scene_settings.longitude_of_show_origin),
            orientation=degrees(scene_settings.show_orientation),
        )
        if scene_settings and scene_settings.use_show_origin_and_orientation
        else None
    )

    # get time markers (cues)
    time_markers = get_time_markers_from_context(context)

    # get cameras
    export_cameras = settings.get("export_cameras", False)
    if export_cameras:
        cameras = get_cameras_from_context(context)
    else:
        cameras = None

    # get validation parameters
    safety_check = getattr(context.scene.skybrush, "safety_check", None)
    validation = SafetyCheckParams(
        max_velocity_xy=(
            safety_check.velocity_xy_warning_threshold if safety_check else 8
        ),
        max_velocity_z=safety_check.velocity_z_warning_threshold if safety_check else 2,
        max_velocity_z_up=(
            safety_check.velocity_z_warning_threshold_up_or_none
            if safety_check
            else None
        ),
        max_acceleration=(
            safety_check.acceleration_warning_threshold if safety_check else 4
        ),
        max_altitude=safety_check.altitude_warning_threshold if safety_check else 150,
        min_distance=safety_check.proximity_warning_threshold if safety_check else 3,
    )

    # get show segments
    show_segments = _get_segments(context=context)

    # shift all time-dependent items so that the time axis of the exported show
    # starts at 0
    delta = -frame_range[0] / context.scene.render.fps
    if delta != 0:
        for trajectory in trajectories.values():
            trajectory.shift_time_in_place(delta)
        for light_program in lights.values():
            light_program.shift_time_in_place(delta)
        if pyro_programs:
            for pyro_program in pyro_programs.values():
                pyro_program.shift_time_in_place(-frame_range[0])
        if yaw_setpoints:
            for yaw_setpoint in yaw_setpoints.values():
                yaw_setpoint.shift_time_in_place(delta)
        time_markers.shift_time_in_place(delta)
        show_segments = {
            k: (v[0] + delta, v[1] + delta) for k, v in show_segments.items()
        }

    renderer_params = {}

    # create Skybrush converter object
    if format is FileFormat.PDF:
        message = "Exporting validation plots to .pdf"
        plots = settings.get("plots", ["stats", "pos", "vel", "drift", "nn"])
        fps = settings.get("output_fps", _default_settings.output_fps)

        log.info(message)
        with report_progress_during_api_operation(message):
            api.generate_plots(
                trajectories=trajectories,
                output=filepath,
                validation=validation,
                plots=plots,
                fps=fps,
                time_markers=time_markers,
            )
    else:
        if format is FileFormat.SKYC:
            message = "Exporting show to Skybrush .skyc format"
            renderer = "skyc"
        elif format is FileFormat.SKYC_AND_PDF:
            message = "Exporting show to .skyc and .pdf formats"
            plots = settings.get("plots", ["stats", "pos", "vel", "drift", "nn"])
            fps = settings.get("output_fps", _default_settings.output_fps)
            renderer = ["skyc", "plot"]
            renderer_params = [
                None,
                {"plots": ",".join(plots), "fps": fps, "single_file": True},
            ]
        elif format is FileFormat.CSV:
            message = "Exporting show to Skybrush .csv format"
            renderer = "csv"
            renderer_params = {
                "fps": settings["output_fps"],
            }
        elif format is FileFormat.DAC:
            message = "Exporting show to HG .dac format"
            renderer = "dac"
            renderer_params = {
                "show_id": 1555,
                "title": "Skybrush show",
            }
        elif format is FileFormat.DDSF:
            message = "Exporting show to Depence .ddsf format"
            renderer = "ddsf"
            renderer_params = {
                "fps": settings["output_fps"],
                "light_fps": settings["light_output_fps"],
            }
        elif format is FileFormat.DROTEK:
            message = "Exporting show to Drotek .json format"
            renderer = "drotek"
            renderer_params = {
                "fps": settings["output_fps"],
                # TODO(ntamas): takeoff_angle?
            }
        elif format is FileFormat.DSS:
            message = "Exporting show to DSS .path format"
            renderer = "dss"
        elif format is FileFormat.DSS3:
            message = "Exporting show to DSS .path3 format"
            renderer = "dss3"
            renderer_params = {
                "fps": settings["output_fps"],
                "light_fps": settings["light_output_fps"],
            }
        elif format is FileFormat.EVSKY:
            message = "Exporting show to EVSKY .essp format"
            renderer = "evsky"
            renderer_params = {
                "fps": settings["output_fps"],
                "light_fps": settings["light_output_fps"],
            }
        elif format is FileFormat.LITEBEE:
            message = "Exporting show to Litebee .bin format"
            renderer = "litebee"
        elif format is FileFormat.VVIZ:
            message = "Exporting show to Finale 3D .vviz format"
            renderer = "vviz"
            renderer_params = {
                "fps": settings["output_fps"],
                "light_fps": settings["light_output_fps"],
            }
        else:
            raise RuntimeError(f"Unhandled format: {format!r}")

        log.info(message)

        with report_progress_during_api_operation(message):
            api.export(
                show_title=show_title,
                show_type=show_type,
                show_location=show_location,
                show_segments=show_segments,
                validation=validation,
                trajectories=trajectories,
                lights=lights,
                pyro_programs=pyro_programs,
                yaw_setpoints=yaw_setpoints,
                output=filepath,
                time_markers=time_markers,
                cameras=cameras,
                renderer=renderer,
                renderer_params=renderer_params,
            )

    log.info("Export finished")
