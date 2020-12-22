"""Background task that is invoked after every frame change and that checks
whether the nearest-neighbor constraints are satisfied in the current
frame.
"""

import bpy

from sbstudio.math.nearest_neighbors import find_nearest_neighbors
from sbstudio.plugin.constants import Collections

# from sbstudio.plugin.utils import debounced

from .base import Task


# TODO(ntamas): make the nearest-neighbor calculation debounced when we have
# lots of drones, but currently we are good with, say 100 drones

# @debounced(delay=0.1)
def run_safety_check(scene, depsgraph):
    safety_check = scene.skybrush.safety_check

    drones = Collections.find_drones(create=False)
    if not drones:
        safety_check.clear_safety_check_result()
        return

    positions = [tuple(drone.matrix_world.translation) for drone in drones.objects]

    max_altitude = (
        safety_check.altitude_warning_threshold
        if safety_check.altitude_warning_enabled
        else None
    )

    if max_altitude is not None:
        drones_over_max_altitude = [
            position for position in positions if position[2] >= max_altitude
        ]
    else:
        drones_over_max_altitude = []

    safety_check.set_safety_check_result(
        nearest_neighbors=find_nearest_neighbors(positions),
        max_altitude=max(position[2] for position in positions),
        drones_over_max_altitude=drones_over_max_altitude,
    )


def ensure_overlays_enabled(*args):
    """Ensures that the safety check overlay is enabled after loading a file."""
    safety_check = bpy.context.scene.skybrush.safety_check
    safety_check.ensure_overlays_enabled_if_needed()


class SafetyCheckTask(Task):
    """Background task that is invoked after every frame change and that checks
    whether the nearest-neighbor constraints are satisfied in the current
    frame.
    """

    functions = {
        "depsgraph_update_post": run_safety_check,
        "frame_change_post": run_safety_check,
        "load_post": ensure_overlays_enabled,
    }
