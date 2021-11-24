"""Background task that is invoked after every frame change and that is
responsible for updating the colors of the drones according to the active
light effects.
"""

from contextlib import contextmanager
from typing import Iterator

from .base import Task

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.materials import get_led_light_color, set_led_light_color
from sbstudio.plugin.utils.evaluator import get_position_of_object

__all__ = ("UpdateLightEffectsTask",)


#: Cache for the "base" color of every drone in the current frame before we
#: apply the light effects on them. Cleared when we move to a new frame. The
#: mapping is keyed by the _ids_ of the drones so we do not hang on to a
#: reference of a drone if the user deletes it and Blender decides to free the
#: associated memory area
_base_color_cache = {}

#: Number of the last frame that was evaluated with `update_light_effects()`
_last_frame = None

#: Suspension counter. Safety checks are suspended if this counter is positive
_suspension_counter = 0

#: White color, used as a base color when no info is available for a newly added
#: drone
WHITE = (1, 1, 1, 1)


def update_light_effects(scene, depsgraph):
    global _last_frame, _base_color_cache, _suspension_counter, WHITE

    # This function is going to be evaluated in every frame, so we should walk
    # the extra mile to ensure that the number of object allocations is as low
    # as possible -- therefore there are lots of in-place modifications of
    # already existing objects

    if _suspension_counter > 0:
        return

    light_effects = scene.skybrush.light_effects
    if not light_effects:
        return

    frame = scene.frame_current
    drones = None

    if _last_frame != frame:
        # Frame changed, clear the base color cache
        _last_frame = frame
        _base_color_cache.clear()

    changed = False

    for effect in light_effects.iter_active_effects_in_frame(frame):
        if drones is None:
            # The only allocations should be concentrated here
            drones = Collections.find_drones().objects
            positions = [get_position_of_object(drone) for drone in drones]
            if not _base_color_cache:
                # This is the first time we are evaluating this frame, so fill
                # the base color cache in parallel to the colors list
                colors = []
                for drone in drones:
                    color = get_led_light_color(drone)
                    colors.append(list(color))
                    _base_color_cache[id(drone)] = color
            else:
                # Initialize the colors list from the cached base colors
                colors = [
                    list(_base_color_cache.get(id(drone), WHITE)) for drone in drones
                ]
            changed = True

        effect.apply_on_colors(colors, positions=positions, frame=frame)

    # If we haven't changed anything, _but_ this is because we have recently
    # disabled or removed the last effect (which we know from the fact that
    # the _base_color_cache is filled), clear the cache and update the colors
    # nevertheless. This is needed to update the screen properly when the last
    # effect is disabled.
    if not changed:
        if _base_color_cache:
            drones = Collections.find_drones().objects
            colors = [list(_base_color_cache.get(id(drone), WHITE)) for drone in drones]
            _base_color_cache.clear()
            changed = True

    if changed:
        for drone, color in zip(drones, colors):
            set_led_light_color(drone, color)


@contextmanager
def suspended_light_effects() -> Iterator[None]:
    """Context manager that suspends safety checks when the context is entered
    and re-enables them when the context is exited.
    """
    global _suspension_counter
    _suspension_counter += 1
    try:
        yield
    finally:
        _suspension_counter -= 1


class UpdateLightEffectsTask(Task):
    """Background task that is invoked after every frame change and that is
    responsible for updating the colors of the drones according to the active
    light effects.
    """

    functions = {
        "depsgraph_update_post": update_light_effects,
        "frame_change_post": update_light_effects,
    }
