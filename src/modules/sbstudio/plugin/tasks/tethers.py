"""Background task that is invoked after every frame change and that handles
tethers of drones and related safety checks in the current frame.
"""

import bpy

from math import atan2, hypot
from typing import List

from sbstudio.math.line_segments import find_closest_points_on_line_segments
from sbstudio.model.types import Coordinate3D
from sbstudio.plugin.constants import Collections

from .base import Task
from sbstudio.plugin.utils.evaluator import get_position_of_object


def get_position_of_objects_in_collection(collection) -> List[Coordinate3D]:
    """Retrieves the current position of objects in the given collection in the
    order they appear in the collection.
    """
    return [get_position_of_object(object) for object in collection.objects]


def run_tethers(scene, depsgraph):

    tethers = scene.skybrush.tethers
    settings = scene.skybrush.settings
    safety_check = scene.skybrush.safety_check

    if not tethers or not settings or not safety_check:
        return

    if settings.use_tethered_drones:
        drones = Collections.find_drones(create=False)
        first_formation = scene.skybrush.storyboard.first_formation
    else:
        drones = None
        first_formation = None

    if not drones or not first_formation:
        tethers.clear_tethers()
        return

    # get home and current positions
    # Note that we retrieve home positions from the first formation, assuming
    # implicitely that it is the takeoff grid and that its position do not
    # change over time. We do this so that we do not need to change frames.
    # This method might be buggy in some corner cases; if that comes up as an
    # issue, a better method will be needed.
    home_positions = get_position_of_objects_in_collection(first_formation)
    positions = get_position_of_objects_in_collection(drones)
    tether_coords = [(a, b) for a, b in zip(home_positions, positions)]

    # perform safety checks
    max_angle = 0
    max_length = 0
    min_distance = 0
    tethers_over_max_angle = []
    tethers_over_max_length = []
    closest_points = []
    if safety_check.enabled:
        # perform tether angle safety checks
        if tethers.angle_warning_enabled:
            angles = [
                atan2(hypot(b[0] - a[0], b[1] - a[1]), b[2] - a[2])
                for a, b in tether_coords
            ]
            max_angle = max(angles)
            tethers_over_max_angle = [
                coords
                for coords, angle in zip(tether_coords, angles)
                if angle > tethers.angle_warning_threshold
            ]

        # perform tether length safety checks
        if tethers.length_warning_enabled:
            lengths = [
                ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
                for a, b in tether_coords
            ]
            max_length = max(lengths)
            tethers_over_max_length = [
                coords
                for coords, length in zip(tether_coords, lengths)
                if length > tethers.length_warning_threshold
            ]

        # perform tether distance safety check
        if tethers.proximity_warning_enabled:
            closest_points, min_distance = find_closest_points_on_line_segments(
                tether_coords
            )

    tethers.update_tethers_and_safety_check_result(
        tethers=tether_coords,
        min_distance=min_distance,
        closest_points=closest_points,
        max_length=max_length,
        tethers_over_max_length=tethers_over_max_length,
        max_angle=max_angle,
        tethers_over_max_angle=tethers_over_max_angle,
    )


def ensure_overlays_enabled():
    """Ensures that the tether overlay is enabled after loading a file."""
    tethers = bpy.context.scene.skybrush.tethers
    tethers.ensure_overlays_enabled_if_needed()


def run_tasks_post_load(*args):
    """Runs all the tasks that should be completed after loading a file."""
    ensure_overlays_enabled()


class UpdateTethersTask(Task):
    """Background task that is invoked after every frame change and that
    updates coordinates of tethers and tether-specific safety checks results.
    """

    functions = {
        "depsgraph_update_post": run_tethers,
        "frame_change_post": run_tethers,
        "load_post": run_tasks_post_load,
    }
