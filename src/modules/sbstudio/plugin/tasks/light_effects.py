"""Background task that is invoked after every frame change and that is
responsible for updating the colors of the drones according to the active
light effects.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

import bpy
import numpy as np

from sbstudio.model.types import MutableRGBAColor, RGBAColor
from sbstudio.plugin.callbacks import final_color_updated_callbacks
from sbstudio.plugin.colors import (
    get_color_of_drone,
    get_colors_of_drones_fast,
)
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.utils.evaluator import get_position_of_object
from sbstudio.plugin.views import redraw_all_3d_views

from .base import Task
from .utils import Suspension

if TYPE_CHECKING:
    from bpy.types import Depsgraph, Object, Scene

__all__ = (
    "UpdateLightEffectsTask",
    "get_base_color_of_drone",
    "get_final_color_of_drone",
    "suspended_light_effects",
)


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
        final_color_updated_callbacks([], [], False)
        return

    random_seq = scene.skybrush.settings.random_sequence_root

    frame = scene.frame_current
    drones = None
    colors = None

    if _last_frame != frame:
        # Frame changed, clear the base and final color cache
        _last_frame = frame
        _base_color_cache.clear()
        _final_color_cache.clear()

    changed = False

    for effect in light_effects.iter_active_effects_in_frame(frame):
        if drones is None:
            # The only allocations should be concentrated here
            drones = Collections.find_drones().objects
            positions = tuple(map(get_position_of_object, drones))
            mapping = scene.skybrush.storyboard.get_mapping_at_frame(frame)
            if not _base_color_cache:
                # This is the first time we are evaluating this frame, so fill
                # the base color cache in parallel to the colors list
                arr = np.empty((len(drones), 4), dtype=np.float32)
                get_colors_of_drones_fast(drones, dest=arr.ravel())
                colors: list[MutableRGBAColor] = arr.tolist()
                for drone, color in zip(drones, colors):
                    _base_color_cache[id(drone)] = color
            else:
                # Initialize the colors list from the cached base colors
                colors = [_base_color_cache.get(id(drone), WHITE) for drone in drones]

            changed = True

        assert colors is not None

        effect.apply_on_colors(
            colors,
            positions=positions,
            mapping=mapping,
            frame=frame,
            random_seq=random_seq,
        )

    # store final colors for later use if there are active light effects
    if changed:
        assert drones is not None
        assert colors is not None
        for drone, color in zip(drones, colors, strict=True):
            _final_color_cache[id(drone)] = color  # ty:ignore[invalid-assignment]

    # If we haven't changed anything, _but_ this is because we have recently
    # disabled or removed the last effect (which we know from the fact that
    # the _base_color_cache is filled), clear the cache and update the colors
    # nevertheless. This is needed to update the screen properly when the last
    # effect is disabled.
    if not changed and _base_color_cache:
        drones = Collections.find_drones().objects
        colors = [_base_color_cache.get(id(drone), WHITE) for drone in drones]
        _base_color_cache.clear()
        changed = True

    # Note that we need to call the callbacks even if we did not change anything,
    # and we imitate a single color change also on last light effect removal
    final_color_updated_callbacks(
        drones or [], cast(Sequence[RGBAColor], colors) or [], changed
    )


def get_base_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) base color of the drone at the current frame
    before any active light effects are applied on it."""
    return _base_color_cache.get(id(drone), get_color_of_drone(drone))


def get_final_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) final color of the drone at the current frame
    after all active light effects are applied on it."""
    return _final_color_cache.get(id(drone), get_base_color_of_drone(drone))


suspended_light_effects = suspension.use
"""Context manager that suspends the calculation of light effects when the
context is entered and re-enables them when the context is exited.
"""


def _update_light_effects_post_load(*args):
    context = bpy.context
    update_light_effects(context.scene, context.evaluated_depsgraph_get())
    redraw_all_3d_views()


class UpdateLightEffectsTask(Task):
    """Background task that is invoked after every frame change and that is
    responsible for updating the colors of the drones according to the active
    light effects.
    """

    functions = {
        "depsgraph_update_post": update_light_effects,
        "frame_change_post": update_light_effects,
        "load_post": _update_light_effects_post_load,
    }
