"""Background task that is invoked after every frame change and that checks
whether the nearest-neighbor constraints are satisfied in the current
frame.
"""

from sbstudio.math.nearest_neighbors import find_nearest_neighbors
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.utils import debounced

from .base import Task


@debounced(delay=0.1)
def run_safety_check(scene, depsgraph):
    safety_check = scene.skybrush.safety_check

    drones = Collections.find_drones(create=False)
    if not drones:
        return

    positions = [tuple(drone.matrix_world.translation) for drone in drones.objects]
    _, _, distance = find_nearest_neighbors(positions)

    # TODO(ntamas): draw the line between the two points on the 3D view!
    safety_check.min_distance = distance


class SafetyCheckTask(Task):
    """Background task that is invoked after every frame change and that checks
    whether the nearest-neighbor constraints are satisfied in the current
    frame.
    """

    functions = {
        "depsgraph_update_post": run_safety_check,
        "frame_change_post": run_safety_check,
    }
