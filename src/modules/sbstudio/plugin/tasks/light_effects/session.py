from __future__ import annotations

from typing import TYPE_CHECKING

from bpy.types import Scene
from numpy import empty, empty_like, float32
from numpy.typing import NDArray

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.light_effects import (
    LightEffect,
    LightEffectEvaluationContext,
    LightEffectUpdate,
)
from sbstudio.plugin.utils.evaluator import ObjectPositions

if TYPE_CHECKING:
    from .updater import LightEffectUpdater


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

    _context: LightEffectEvaluationContext | None = None
    """Context of the light effect update session, passed on to the light effect itself.
    Contains all data required to evaluate the effect.
    """

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
        assert self._frame is not None
        effect.apply_on_colors(self._ensure_context(), frame=self._frame)

    def _ensure_context(self) -> LightEffectEvaluationContext:
        """Returns the context of the update session, creating it if needed."""
        assert self._scene is not None
        assert self._frame is not None

        if self._context is None:
            drones = Collections.find_drones().objects
            base_colors = self._owner._create_mutable_color_array_for_drones(drones)
            self._context = LightEffectEvaluationContext(
                drones=drones,
                positions=ObjectPositions(drones),
                mapping=self._scene.skybrush.storyboard.get_mapping_at_frame(
                    self._frame
                ),
                # empty mask is enough because we will erase it anyway every time we
                # evaluate a new effect
                mask=empty((len(drones),), dtype=bool),
                random_seq=self._scene.skybrush.settings.random_sequence_root,
                backdrop=base_colors,
                colors=empty_like(base_colors),
            )

        return self._context

    def reset(self, scene: Scene | None = None, frame: int | None = None) -> None:
        """Resets the update session and prepares it for updating the colors of the
        drones in the given scene and frame.
        """
        self._scene = scene
        self._frame = frame

        self._final_colors = None
        self._context = None

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

        state = self._context
        if state is None and self._owner._has_base_colors():
            # No color updates were applied in this session but the user has just turned
            # off the last color effect so pretend that there were some effects
            state = self._ensure_context()
            clear_base_color_cache_at_end = True
        else:
            clear_base_color_cache_at_end = False

        if state is None:
            # No color updates were applied and it has been like this even in the
            # previous frame so no need to calculate the final colors
            return LightEffectUpdate.NOP

        self._final_colors = state.backdrop
        if clear_base_color_cache_at_end:
            self._owner._clear_base_colors()

        return LightEffectUpdate(state.drones, state.positions, state.backdrop, True)
