"""Background task that is invoked after every frame change and that is
responsible for updating the colors of the drones according to the active
light effects.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

import bpy
import numpy as np
from bpy.types import CollectionObjects

from sbstudio.model.types import MutableRGBAColor, RGBAColor
from sbstudio.plugin.callbacks import final_color_updated_callbacks
from sbstudio.plugin.colors import (
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
    "suspended_color_update_callbacks",
    "suspended_light_effects",
)


light_effect_suspension = Suspension()
"""Object to manage the suspension logic for the light effect task."""

color_update_callbacks_suspension = Suspension()
"""Object to manage the suspension logic for color update callbacks."""

WHITE: RGBAColor = (1, 1, 1, 1)
"""White color, used as a base color when no info is available for a newly added
drone.
"""


class ColorCache:
    """Class that stores the base and final color of every drone in the current frame.

    The class is also responsible for ensuring that the base colors are provided to
    users of class instances in an immutable manner as the calculation of the final
    colors always need to start from the actual base colors of the drones, which are
    not supposed to be modified by the light effects.
    """

    _base_colors: dict[int, RGBAColor]
    """Cache for the "base" color of every drone in the current frame before we
    apply the light effects on them. Cleared when we move to a new frame. The
    mapping is keyed by the _ids_ of the drones so we do not hang on to a
    reference of a drone if the user deletes it and Blender decides to free the
    associated memory area."""

    _final_colors: dict[int, RGBAColor]
    """Cache for the "final" color of every drone in the current frame after we
    apply the light effects on them. Cleared when there are no light effects. The
    mapping is keyed by the _ids_ of the drones so we do not hang on to a
    reference of a drone if the user deletes it and Blender decides to free the
    associated memory area."""

    _last_frame: int | None = None
    """Index of the last frame that was evaluated with `update_light_effects()`"""

    def __init__(self):
        self._base_colors = {}
        self._final_colors = {}

    def clear_final_colors(self):
        """Clears the final color cache."""
        self._final_colors.clear()

    def get_base_color_of_drone(self, drone: Object) -> RGBAColor:
        """Returns the (cached) base color of the drone at the current frame
        before any active light effects are applied on it.
        """
        return self._base_colors.get(id(drone)) or WHITE

    def get_final_color_of_drone(self, drone: Object) -> RGBAColor:
        """Returns the (cached) final color of the drone at the current frame
        after all active light effects are applied on it.
        """
        return self._final_colors.get(id(drone)) or self.get_base_color_of_drone(drone)

    def create_mutable_color_array_for_drones(
        self, drones: CollectionObjects
    ) -> list[MutableRGBAColor]:
        """Creates two numpy arrays for the base and final colors of the given drones.

        The first array contains the base colors of the drones, while the second
        array contains the final colors of the drones. The arrays are created in
        a way that they can be used directly in the light effect calculations.

        Args:
            drones: Sequence of drone objects.

        Returns:
            A tuple containing two numpy arrays: (base_colors_array, final_colors_array).
        """
        colors: list[MutableRGBAColor]

        if not self._base_colors:
            # This is the first time we are evaluating this frame, so fill
            # the base color cache in parallel to the colors list
            arr = np.empty((len(drones), 4), dtype=np.float32)
            get_colors_of_drones_fast(drones, dest=arr.ravel())
            colors = arr.tolist()
            for drone, color in zip(drones, colors):
                self._base_colors[id(drone)] = tuple(color)
        else:
            # Initialize the colors list from the cached base colors
            colors = [
                list(self._base_colors.get(id(drone)) or WHITE) for drone in drones
            ]

        return colors

    def store_final_colors(
        self, drones: CollectionObjects, colors: list[MutableRGBAColor]
    ) -> Sequence[RGBAColor]:
        """Stores the final colors of the given drones in the cache."""
        for drone, color in zip(drones, colors, strict=True):
            self._final_colors[id(drone)] = color  # ty:ignore[invalid-assignment]
        return cast(Sequence[RGBAColor], colors)

    def notify_frame_change(self, frame: int) -> None:
        """Notifies the cache that the frame might have changed."""
        if self._last_frame != frame:
            self._last_frame = frame
            self._base_colors.clear()

    def notify_no_effects_applied(self) -> Sequence[RGBAColor] | None:
        """Notifies the cache that no light effects were applied in the current frame.

        Args:
            drones: sequence of drone objects.

        Returns:
            sequence of final colors of the drones to apply, or None if we know that the
            drones are using the right color
        """
        if not self._base_colors:
            return None

        drones = Collections.find_drones().objects
        colors = [self._base_colors.get(id(drone)) or list(WHITE) for drone in drones]
        self._base_colors.clear()
        return cast(Sequence[RGBAColor], colors)


_color_cache: ColorCache = ColorCache()
"""Global instance of the color cache to be used by the light effect task."""


@light_effect_suspension.wrap
def update_light_effects(scene: Scene, depsgraph: Depsgraph):
    global _color_cache, WHITE

    # This function is going to be evaluated in every frame, so we should walk
    # the extra mile to ensure that the number of object allocations is as low
    # as possible -- therefore there are lots of in-place modifications of
    # already existing objects

    light_effects = scene.skybrush.light_effects
    if not light_effects or not light_effects.enabled:
        _color_cache.clear_final_colors()
        final_color_updated_callbacks([], [], False)
        return

    random_seq = scene.skybrush.settings.random_sequence_root

    frame = scene.frame_current

    drones: CollectionObjects | None = None
    colors: Sequence[MutableRGBAColor] | None = None

    _color_cache.notify_frame_change(frame)

    has_active_effects = False

    for effect in light_effects.iter_active_effects_in_frame(frame):
        if drones is None:
            # The only allocations should be concentrated here
            drones = Collections.find_drones().objects
            drones_tuple = tuple(drones.values())
            positions = [get_position_of_object(drone) for drone in drones]
            mapping = scene.skybrush.storyboard.get_mapping_at_frame(frame)
            colors = _color_cache.create_mutable_color_array_for_drones(drones)
            has_active_effects = True

        assert colors is not None

        effect.apply_on_colors(
            colors,
            drones=drones_tuple,
            positions=positions,
            mapping=mapping,
            frame=frame,
            random_seq=random_seq,
        )

    if has_active_effects:
        # store final colors for later use if there are active light effects
        assert drones is not None
        assert colors is not None
        final_colors = _color_cache.store_final_colors(drones, colors)
    else:
        # let the color cache know that there were no active light effects in this frame
        # so it can just use the base colors as the final colors
        final_colors = _color_cache.notify_no_effects_applied()
        if final_colors is not None:
            # Need one final update if the last effect has just been turned off
            drones = Collections.find_drones().objects
            has_active_effects = True

    # Wrap the callback calls to our suspension logic internally
    if not color_update_callbacks_suspension.active:
        # Note that we need to call the callbacks even if we did not change anything,
        # and we imitate a single color change also on last light effect removal
        final_color_updated_callbacks(
            drones or [], final_colors or [], has_active_effects
        )


def get_base_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) base color of the drone at the current frame
    before any active light effects are applied on it."""
    global _color_cache
    return _color_cache.get_base_color_of_drone(drone)


def get_final_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) final color of the drone at the current frame
    after all active light effects are applied on it."""
    global _color_cache
    return _color_cache.get_final_color_of_drone(drone)


suspended_light_effects = light_effect_suspension.use
"""Context manager that suspends the calculation of light effects when the
context is entered and re-enables them when the context is exited.

Useful when sampling only the positions of the drones (or any other information that
does not require the evaluation of light effects). Implies the suspension of color
update callbacks as well since the colors are not going to be updated.
"""

suspended_color_update_callbacks = color_update_callbacks_suspension.use
"""Context manager that suspends the execution of color update callbacks when
the context is entered and re-enables them when the context is exited. Light
effects are still calculated and cached.

Useful when sampling the LED colors of the drones in a manner that does not require the
3D viewport to be updated.
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
