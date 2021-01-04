"""Background task that is invoked after every frame change and that is
responsible for updating the colors of the drones according to the active
light effects.
"""

from .base import Task

from sbstudio.model.types import RGBAColor
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.materials import get_led_light_color, set_led_light_color
from sbstudio.plugin.utils.evaluator import get_position_of_object

__all__ = ("UpdateLightEffectsTask",)


def update_light_effects(scene, depsgraph):
    # This function is going to be evaluated in every frame, so we should walk
    # the extra mile to ensure that the number of object allocations is as low
    # as possible -- therefore there are lots of in-place modifications of
    # already existing objects

    light_effects = scene.skybrush.light_effects
    if not light_effects:
        return

    frame = scene.frame_current
    drones = None

    # TODO(ntamas): if we are standing in a frame with only one effect enabled,
    # and we disable that effect, the colors of the drones will keep that color.
    # We should refresh all of them instead.

    changed = False

    for effect in light_effects.iter_active_effects_in_frame(frame):
        if drones is None:
            # The only allocations should be concentrated here
            drones = Collections.find_drones().objects
            positions = [get_position_of_object(drone) for drone in drones]
            colors = [list(get_led_light_color(drone)) for drone in drones]
            changed = True

        for index, position in enumerate(positions):
            effect.apply_on_color(colors[index], position=positions[index], frame=frame)

    if changed:
        for drone, color in zip(drones, colors):
            set_led_light_color(drone, color)


class UpdateLightEffectsTask(Task):
    """Background task that is invoked after every frame change and that is
    responsible for updating the colors of the drones according to the active
    light effects.
    """

    functions = {
        "depsgraph_update_post": update_light_effects,
        "frame_change_post": update_light_effects,
    }
