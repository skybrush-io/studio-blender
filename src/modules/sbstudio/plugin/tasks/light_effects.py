"""Background task that is invoked after every frame change and that is
responsible for updating the colors of the drones according to the active
light effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import bpy
from bpy.types import CollectionObjects, Object
from numpy import empty, float32
from numpy.typing import NDArray

from sbstudio.api.types import Mapping
from sbstudio.model.types import RGBAColor
from sbstudio.plugin.callbacks import final_color_updated_callbacks
from sbstudio.plugin.colors import (
    get_colors_of_drones_fast,
)
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model import LightEffect
from sbstudio.plugin.model.light_effects import LightEffectUpdate
from sbstudio.plugin.utils.evaluator import ObjectPositions
from sbstudio.plugin.views import redraw_all_3d_views
from sbstudio.utils import measure_time

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


class LightEffectUpdater:
    """Manager object responsible for executing the process that updates the colors
    of the drones in a given frame based on a list of dynamically calculated light
    effects.

    The process starts from the _base colors_, i.e. the colors that correspond to the
    drones in the frame based on keyframes and other Blender-specific things. Light
    effects are overlaid on base colors with standard compositing rules, and the final
    colors are then stored in a cache for the current frame. A separate set of light
    effect callbacks are responsible for displaying the final calculated colors in a
    way that makes sense for the end user. This includes (but is not limited to):

      - propagating the calculated colors either back to the colors of the drones
      - drawing an overlay of colored boxes on top of the drones in the 3D view
    """

    _base_colors: NDArray[float32]
    """NumPy array of shape (N, 4) containing the base color of every drone
    that was cached for the current frame."""

    _drone_to_row_index: dict[Object, int]
    """Mapping from drone object IDs to row indices in `_base_colors_array`."""

    _last_frame: int | None = None
    """Index of the last frame that was evaluated with `update_light_effects()`"""

    _session: LightEffectUpdateSession
    """The light effect update session that allows the user to apply light effects
    on the current array of drones and base colors, and to retrieve the final colors
    and the color updates to perform at the end.
    """

    def __init__(self):
        self._base_colors = empty((0, 4), dtype=float32)
        self._drone_to_row_index = {}
        self._session = LightEffectUpdateSession(self)

    def get_base_color_of_drone(self, drone: Object) -> RGBAColor:
        """Returns the (cached) base color of the drone at the current frame
        before any active light effects are applied on it.

        The returned value is a copy of the color in the cache. It can be modified, but
        the modifications will not affect the cached value.
        """
        idx = self._drone_to_row_index.get(drone)
        if idx is not None:
            return tuple(self._base_colors[idx])
        return WHITE

    def get_final_color_of_drone(self, drone: Object) -> RGBAColor:
        """Returns the (cached) final color of the drone at the current frame
        after all active light effects are applied on it.
        """
        idx = self._drone_to_row_index.get(drone)
        if idx is None:
            return WHITE

        final_colors = self._session._final_colors
        return (
            tuple(final_colors[idx])
            if final_colors is not None
            else tuple(self._base_colors[idx])
        )

    def update(self, scene: Scene) -> LightEffectUpdate:
        """Updates the colors of the drones in the given scene based on the active
        light effects.

        Args:
            scene: The scene that is being updated.

        Returns:
            the updates to apply to the drones in the scene, or `LightEffectUpdate.NOP`
            if no updates are to be applied
        """
        light_effects = scene.skybrush.light_effects
        if not light_effects or not light_effects.enabled:
            self._ensure_session_not_running()
            self._session.reset()
            return LightEffectUpdate.NOP

        frame = scene.frame_current
        if self._last_frame != frame:
            self._last_frame = frame
            self._clear_base_colors()

        try:
            self._session.reset(scene, frame)
            for effect in light_effects.iter_active_effects_in_frame(frame):
                with measure_time(
                    f"Applying light effect: {effect.name}", enabled=False
                ):
                    self._session.apply_effect(effect)
        finally:
            updates = self._session.finalize()

        return updates

    def _clear_base_colors(self) -> None:
        """Clears the base color cache."""
        self._drone_to_row_index.clear()
        self._base_colors = empty((0, 4), dtype=float32)

    def _create_mutable_color_array_for_drones(
        self, drones: CollectionObjects
    ) -> NDArray[float32]:
        """Creates a mutable color array from the given collection of drones that can
        be used during light effect calculations to update the colors.

        The returned array contains as many rows as the number of drones in the input
        collection. The i-th row stores the color of the i-th drone, in RGBA order.
        """
        n = len(drones)
        if not self._drone_to_row_index or n != self._base_colors.shape[0]:
            # Either we have no base colors yet, or the number of drones has changed.
            # Query the base colors from the drones.
            #
            # This is not 100% correct:
            #
            # - If the number of drones change, the colors that we query here already
            #   have the light effects applied in the current frame. ¯\_(ツ)_/¯
            # - If the number of drones remains the same but the user reorders the
            #   Drones collection, the base color array is not updated.
            #
            # These are shortcomings that we can live with for now as they can easily
            # be fixed by changing to a different frame and then back to the current
            # frame.
            self._base_colors = empty((n, 4), dtype=float32)
            get_colors_of_drones_fast(drones, dest=self._base_colors.ravel())
            self._drone_to_row_index = {drone: i for i, drone in enumerate(drones)}

        return self._base_colors.copy()

    def _ensure_session_not_running(self) -> None:
        """Ensures that no session is currently active."""
        if self._session.active:
            raise RuntimeError(
                "Cannot start a new update session while another session is active."
            )

    def _has_base_colors(self) -> bool:
        """Returns whether there are already some cached base colors in the cache."""
        return bool(self._drone_to_row_index)


@dataclass(frozen=True)
class LightEffectUpdateSessionState:
    """Class that stores the state of the light effect update session."""

    drones: CollectionObjects
    """The collection of drones being updated in this session."""

    positions: ObjectPositions
    """The positions of the drones."""

    mapping: Mapping | None
    """Mapping from drone indices to the indices of the markers in the current
    formation that is in effect at the given frame. `None` if the frame is not in a
    formation or if we do not know the mapping for that formation.
    """

    colors: NDArray[float32]
    """Array in which the final colors of the drones are being stored."""


class LightEffectUpdateSession:
    """Context manager that manages the update session of the color cache."""

    _owner: LightEffectUpdater
    """The light effect updater that owns this update session."""

    _scene: Scene | None
    """The scene that is being updated."""

    _frame: int | None
    """The frame that is being updated."""

    _final_colors: NDArray[float32] | None = None
    """Array of the final colors of the drones in the current frame, after we have
    applied the light effects on them. One drone per row. Populated when calling the
    `finalize()` method.

    The order of the colors in this list is the same as the order of the drones in
    the `drones` attribute of the `_State` object returned by the `get_state()` method.
    """

    _state: LightEffectUpdateSessionState | None = None
    """Mutable part of the update session."""

    def __init__(self, color_cache: LightEffectUpdater):
        self._owner = color_cache
        self.reset(None, None)

    @property
    def active(self) -> bool:
        """Returns whether the session is active."""
        return self._scene is not None

    def apply_effect(self, effect: LightEffect) -> None:
        """Applies the given light effect to the current state of the session.

        Must be called only if the session is active.
        """
        assert self._scene is not None
        assert self._frame is not None

        random_seq = self._scene.skybrush.settings.random_sequence_root
        state = self._ensure_state()
        effect.apply_on_colors(
            state.colors,
            drones=state.drones,
            positions=state.positions,
            mapping=state.mapping,
            frame=self._frame,
            random_seq=random_seq,
        )

    def _ensure_state(self) -> LightEffectUpdateSessionState:
        """Returns the state of the update session, creating it if needed."""
        assert self._scene is not None
        assert self._frame is not None

        if self._state is None:
            drones = Collections.find_drones().objects
            self._state = LightEffectUpdateSessionState(
                drones=drones,
                colors=self._owner._create_mutable_color_array_for_drones(drones),
                positions=ObjectPositions(drones),
                mapping=self._scene.skybrush.storyboard.get_mapping_at_frame(
                    self._frame
                ),
            )

        return self._state

    def reset(self, scene: Scene | None = None, frame: int | None = None) -> None:
        """Resets the update session and prepares it for updating the colors of the
        drones in the given scene and frame.
        """
        self._scene = scene
        self._frame = frame

        self._final_colors = None
        self._state = None

    def finalize(self) -> LightEffectUpdate:
        """Finalizes the current session and the drones and their final colors to be
        applied to the scene.

        Returns:
            A tuple containing the drones and their final colors, and whether there
            was at least one active light effect or the last active effect was turned
            off just now
        """
        try:
            return self._finalize()
        finally:
            self._scene = None
            self._frame = None

    def _finalize(self) -> LightEffectUpdate:
        """Stores the final colors of the given drones from the state if at least one
        effect was applied, or copies the colors from the base color cache if no effects
        were applied.
        """
        assert self._scene is not None
        assert self._frame is not None

        state = self._state
        if state is None and self._owner._has_base_colors():
            # No color updates were applied in this session but the user has just turned
            # off the last color effect so pretend that there were some effects
            state = self._ensure_state()
            clear_base_color_cache_at_end = True
        else:
            clear_base_color_cache_at_end = False

        if state is None:
            # No color updates were applied and it has been like this even in the
            # previous frame so no need to calculate the final colors
            return LightEffectUpdate.NOP

        self._final_colors = state.colors
        if clear_base_color_cache_at_end:
            self._owner._clear_base_colors()

        return LightEffectUpdate(state.drones, state.positions, state.colors, True)


_light_effect_updater: LightEffectUpdater = LightEffectUpdater()
"""Single instance of the light effect updater process."""


@light_effect_suspension.wrap
def update_light_effects(scene: Scene, depsgraph: Depsgraph):
    updates = _light_effect_updater.update(scene)
    if not color_update_callbacks_suspension.active:
        final_color_updated_callbacks(updates)


def get_base_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) base color of the drone at the current frame
    before any active light effects are applied on it."""
    return _light_effect_updater.get_base_color_of_drone(drone)


def get_final_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) final color of the drone at the current frame
    after all active light effects are applied on it."""
    return _light_effect_updater.get_final_color_of_drone(drone)


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
