from bpy.types import CollectionObjects, Object, Scene
from numpy import empty, float32
from numpy.typing import NDArray

from sbstudio.model.types import RGBAColor
from sbstudio.plugin.colors import get_colors_of_drones_fast
from sbstudio.plugin.model.light_effects import LightEffectUpdate
from sbstudio.utils import measure_time

from .session import LightEffectUpdateSession

__all__ = ("LightEffectUpdater",)

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
