"""Background task that is invoked after every frame change and that checks
whether the nearest-neighbor constraints are satisfied in the current
frame.
"""

import bpy

from contextlib import contextmanager
from math import hypot
from typing import Iterator

from sbstudio.math.nearest_neighbors import find_nearest_neighbors
from sbstudio.plugin.constants import Collections
from sbstudio.utils import LRUCache

# from sbstudio.plugin.utils import debounced

from .base import Task


# TODO(ntamas): make the nearest-neighbor calculation debounced when we have
# lots of drones, but currently we are good with, say 100 drones

#: Cache that stores the positions in the last few frames visited by the user
#: in the hope that we can estimate the velocities from it in the current frame
_position_snapshot_cache = LRUCache(5)

#: Suspension counter. Safety checks are suspended if this counter is positive
_suspension_counter = 0

#: Zero velocity tuple, used frequently in velocity estimations when no data is
#: available
_ZERO = (0.0, 0.0, 0.0)


def create_position_snapshot_for_drones_in_collection(collection, *, frame):
    """Create a dictionary mapping the names of the drones in the given
    collection to their positions.
    """
    return {
        drone.name: tuple(drone.matrix_world.translation)
        for drone in collection.objects
    }


def estimate_velocities_of_drones_at_frame(snapshot, *, frame, scene):
    """Attempts to estimate the velocities of the drones in the given frame,
    using the given snapshot for the frame and the current data in the
    position snapshot cache.
    """
    global _position_snapshot_cache, _ZERO

    if frame <= scene.frame_start:
        # Estimate zero velocities at the start of the scene
        return {drone_name: _ZERO for drone_name in snapshot}

    # TODO(ntamas): use a smarter algorithm that tries to evaluate the F-curves
    # and constraints of each drone

    threshold = 5  # max frame difference that we accept
    best, best_diff = None, threshold + 1

    for item in _position_snapshot_cache.items():
        other_frame, other_snapshot = item
        diff = abs(other_frame - frame)
        if diff == 0:
            continue

        # If we have data from both the past and the future, prefer the past
        is_better = diff < best_diff or (diff == best_diff and other_frame < frame)

        if is_better:
            best, best_diff = item, diff

    if best is not None:
        # Okay, got a nice frame candidate
        other_frame, other_snapshot = best
        diff = (frame - other_frame) / scene.render.fps

        result = {}
        for drone_name, curr in snapshot.items():
            prev = other_snapshot.get(drone_name)
            result[drone_name] = (
                (
                    (curr[0] - prev[0]) / diff,
                    (curr[1] - prev[1]) / diff,
                    (curr[2] - prev[2]) / diff,
                )
                if prev is not None
                else _ZERO
            )

        return result

    return {drone_name: _ZERO for drone_name in snapshot}


# @debounced(delay=0.1)
def run_safety_check(scene, depsgraph):
    global _suspension_counter
    if _suspension_counter > 0:
        return

    safety_check = scene.skybrush.safety_check

    if safety_check.enabled:
        drones = Collections.find_drones(create=False)
    else:
        drones = None

    if not drones:
        safety_check.clear_safety_check_result()
        return

    # Get the thresholds from the safety check object
    if safety_check.altitude_warning_threshold:
        max_altitude = safety_check.altitude_warning_threshold
    else:
        max_altitude = None
    if safety_check.velocity_warning_enabled:
        max_velocity_xy = safety_check.velocity_xy_warning_threshold
        max_velocity_z_down = safety_check.effective_velocity_z_threshold_down
        max_velocity_z_up = safety_check.effective_velocity_z_threshold_up
    else:
        max_velocity_xy, max_velocity_z_up, max_velocity_z_down = None, None, None

    frame = scene.frame_current
    snapshot = create_position_snapshot_for_drones_in_collection(drones, frame=frame)
    _position_snapshot_cache[frame] = snapshot

    # Get formation status as a string
    storyboard = scene.skybrush.storyboard
    formation_status = storyboard.get_formation_status_at_frame(frame)

    # Check min/max altitude
    positions = list(snapshot.values())
    if max_altitude is not None:
        drones_over_max_altitude = [
            position for position in positions if position[2] >= max_altitude
        ]
    else:
        drones_over_max_altitude = []
    max_altitude_found = (
        max(position[2] for position in positions) if positions else 0.0
    )
    min_altitude_found = (
        min(position[2] for position in positions) if positions else 0.0
    )

    # Check nearest neighbors
    nearest_neighbors = find_nearest_neighbors(positions)

    # Check velocities
    max_velocity_xy_found = None
    velocity_snapshot = estimate_velocities_of_drones_at_frame(
        snapshot, frame=frame, scene=scene
    )
    velocities = list(velocity_snapshot.values())

    max_velocity_xy_found = (
        max(hypot(vel[0], vel[1]) for vel in velocities) if velocities else 0.0
    )
    if max_velocity_xy is not None:
        drones_over_max_velocity_xy = [
            snapshot.get(name, _ZERO)
            for name, vel in velocity_snapshot.items()
            if hypot(vel[0], vel[1]) > max_velocity_xy
        ]
    else:
        drones_over_max_velocity_xy = []

    upper = max(0.0, max(vel[2] for vel in velocities)) if velocities else 0.0
    lower = min(0.0, min(vel[2] for vel in velocities)) if velocities else 0.0
    if max_velocity_z_up is not None and max_velocity_z_down is not None:
        drones_over_max_velocity_z = [
            snapshot.get(name, _ZERO)
            for name, vel in velocity_snapshot.items()
            if vel[2] > max_velocity_z_up or vel[2] < -max_velocity_z_down
        ]
    else:
        drones_over_max_velocity_z = []

    safety_check.set_safety_check_result(
        formation_status=formation_status,
        nearest_neighbors=nearest_neighbors,
        min_altitude=min_altitude_found,
        max_altitude=max_altitude_found,
        drones_over_max_altitude=drones_over_max_altitude,
        max_velocity_xy=max_velocity_xy_found,
        drones_over_max_velocity_xy=drones_over_max_velocity_xy,
        max_velocity_z_up=upper,
        max_velocity_z_down=abs(lower),
        drones_over_max_velocity_z=drones_over_max_velocity_z,
    )


def ensure_overlays_enabled():
    """Ensures that the safety check overlay is enabled after loading a file."""
    safety_check = bpy.context.scene.skybrush.safety_check
    safety_check.ensure_overlays_enabled_if_needed()


def invalidate_caches(clear_result: bool = False):
    """Invalidates the caches used by the safety check feature.

    This function should be called when the plugin makes radical changes to the
    current scene; for instance, after re-planning transitions.
    """
    global _position_snapshot_cache
    _position_snapshot_cache.clear()

    if clear_result:
        safety_check = bpy.context.scene.skybrush.safety_check
        safety_check.clear_safety_check_result()


def run_tasks_post_load(*args):
    """Runs all the tasks that should be completed after loading a file."""
    invalidate_caches()
    ensure_overlays_enabled()


@contextmanager
def suspended_safety_checks() -> Iterator[None]:
    """Context manager that suspends safety checks when the context is entered
    and re-enables them when the context is exited.
    """
    global _suspension_counter
    _suspension_counter += 1
    try:
        yield
    finally:
        _suspension_counter -= 1


class SafetyCheckTask(Task):
    """Background task that is invoked after every frame change and that checks
    whether the nearest-neighbor constraints are satisfied in the current
    frame.
    """

    functions = {
        "depsgraph_update_post": run_safety_check,
        "frame_change_post": run_safety_check,
        "load_post": run_tasks_post_load,
    }
