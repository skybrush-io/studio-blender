"""Background task that is invoked after every frame change and that is
responsible for updating the colors of the drones according to the active
light effects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from sbstudio.model.types import MutableRGBAColor, RGBAColor
from sbstudio.plugin.colors import (
    get_color_of_drone,
    get_colors_of_drones_fast,
    set_color_of_drone,
)
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.overlays.light_effect import LightEffectOverlayMarker
from sbstudio.plugin.utils.evaluator import get_position_of_object

from .base import Task
from .utils import Suspension

if TYPE_CHECKING:
    from bpy.types import Depsgraph, Object, Scene

__all__ = ("UpdateLightEffectsTask", "suspended_light_effects")


_base_color_cache: dict[int, RGBAColor] = {}
"""Cache for the "base" color of every drone in the current frame before we
apply the light effects on them. Cleared when we move to a new frame. The
mapping is keyed by the _ids_ of the drones so we do not hang on to a
reference of a drone if the user deletes it and Blender decides to free the
associated memory area."""

_final_color_cache: dict[int, RGBAColor] = {}
"""Cache for the "final" color of every drone in the current frame after we
apply the light effects on them. Cleared when there are no light effects. The
mapping is keyed by the _ids_ of the drones so we do not hang on to a
reference of a drone if the user deletes it and Blender decides to free the
associated memory area."""

_last_frame: int | None = None
"""Number of the last frame that was evaluated with `update_light_effects()`"""

suspension = Suspension()
"""Object to manage the suspension logic for the light effect task."""

WHITE: RGBAColor = (1, 1, 1, 1)
"""White color, used as a base color when no info is available for a newly added
drone.
"""


@suspension.wrap
def update_light_effects(scene: Scene, depsgraph: Depsgraph):
    global _last_frame, _base_color_cache, _final_color_cache, WHITE

    # This function is going to be evaluated in every frame, so we should walk
    # the extra mile to ensure that the number of object allocations is as low
    # as possible -- therefore there are lots of in-place modifications of
    # already existing objects

    light_effects = scene.skybrush.light_effects
    if not light_effects or not light_effects.enabled:
        _final_color_cache.clear()
        light_effects.clear_overlay_markers()
        return

    random_seq = scene.skybrush.settings.random_sequence_root

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
            mapping = scene.skybrush.storyboard.get_mapping_at_frame(frame)
            if not _base_color_cache:
                # This is the first time we are evaluating this frame, so fill
                # the base color cache in parallel to the colors list
                arr = np.zeros((len(drones), 4), dtype=np.float32)
                get_colors_of_drones_fast(drones, dest=arr.ravel())
                colors: list[MutableRGBAColor] = arr.tolist()
                for drone, color in zip(drones, colors):
                    _base_color_cache[id(drone)] = color
            else:
                # Initialize the colors list from the cached base colors
                colors = [
                    _base_color_cache.get(id(drone)) or list(WHITE) for drone in drones
                ]

            changed = True

        effect.apply_on_colors(
            colors,
            positions=positions,
            mapping=mapping,
            frame=frame,
            random_seq=random_seq,
        )

    # If we haven't changed anything, _but_ this is because we have recently
    # disabled or removed the last effect (which we know from the fact that
    # the _base_color_cache is filled), clear the cache and update the colors
    # nevertheless. This is needed to update the screen properly when the last
    # effect is disabled.
    has_active_effects = changed
    if not changed and _base_color_cache:
        drones = Collections.find_drones().objects
        colors = [_base_color_cache.get(id(drone)) or list(WHITE) for drone in drones]
        _base_color_cache.clear()
        has_active_effects = False
        changed = True

    overlay_markers: list[LightEffectOverlayMarker] = []
    if changed:
        assert drones is not None

        for drone, color in zip(drones, colors):
            _final_color_cache[id(drone)] = color
            match light_effects.visualization:
                case "MARKERS":
                    if has_active_effects:
                        position = get_position_of_object(drone)
                        overlay_markers.append((position, color))
                case "MATERIALS":
                    set_color_of_drone(drone, color)
                case _:
                    pass
    light_effects.update_overlay_markers(overlay_markers)


def get_final_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) final color of the drone at the current frame
    after all active light effects are applied on it."""
    return _final_color_cache.get(id(drone)) or get_color_of_drone(drone)


suspended_light_effects = suspension.use
"""Context manager that suspends the calculation of light effects when the
context is entered and re-enables them when the context is exited.
"""


class UpdateLightEffectsTask(Task):
    """Background task that is invoked after every frame change and that is
    responsible for updating the colors of the drones according to the active
    light effects.
    """

    functions = {
        "depsgraph_update_post": update_light_effects,
        "frame_change_post": update_light_effects,
    }
