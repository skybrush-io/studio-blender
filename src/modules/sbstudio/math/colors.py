from enum import auto, IntEnum
from typing import Callable, List, MutableSequence, Sequence

__all__ = ("blend_in_place", "BlendMode")


class BlendMode(IntEnum):
    NORMAL = auto()
    MULTIPLY = auto()
    SCREEN = auto()
    DARKEN = auto()
    LIGHTEN = auto()
    OVERLAY = auto()
    SOFT_LIGHT = auto()
    HARD_LIGHT = auto()

    # Do not change the order of items above to remain compatible with already
    # saved Blender scenes.
    #
    # When adding a new blend mode, also add a new function to the end of
    # _blend_funcs below

    @property
    def description(self) -> str:
        return self.name.lower().replace("_", " ").capitalize()


def _blend_normal(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    for i in range(3):
        backdrop[i] = a * source[i] + b * backdrop[i]


def _blend_multiply(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    for i in range(3):
        backdrop[i] = a * backdrop[i] * source[i] + b * backdrop[i]


def _blend_screen(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    for i in range(3):
        backdrop[i] = a * (1 - (1 - backdrop[i]) * (1 - source[i])) + b * backdrop[i]


def _blend_darken(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    for i in range(3):
        backdrop[i] = a * min(backdrop[i], source[i]) + b * backdrop[i]


def _blend_lighten(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    for i in range(3):
        backdrop[i] = a * max(backdrop[i], source[i]) + b * backdrop[i]


def _blend_overlay(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    for i in range(3):
        if backdrop[i] >= 0.5:
            backdrop[i] = (
                a * (1 - (2 - 2 * backdrop[i]) * (1 - source[i])) + b * backdrop[i]
            )
        else:
            backdrop[i] = a * (2 * backdrop[i]) * source[i] + b * backdrop[i]


def _blend_hard_light(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    for i in range(3):
        if source[i] <= 0.5:
            backdrop[i] = a * backdrop[i] * (2 * source[i]) + b * backdrop[i]
        else:
            backdrop[i] = (
                a * (1 - (1 - backdrop[i]) * (2 - 2 * source[i])) + b * backdrop[i]
            )


def _blend_soft_light(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    # There are multiple variants for this mode; the variant below is the W3C
    # recommendation, _not_ the one in Photoshop.
    # See: https://imagineer.in/blog/math-behind-blend-modes/
    for i in range(3):
        if source[i] <= 0.5:
            backdrop[i] = (
                a
                * (backdrop[i] - (1 - 2 * source[i]) * backdrop[i] * (1 - backdrop[i]))
                + b * backdrop[i]
            )
        else:
            if backdrop[i] <= 0.25:
                d = ((16 * backdrop[i] - 12) * backdrop[i] + 4) * backdrop[i]
            else:
                d = backdrop[i] ** 0.5
            backdrop[i] = (
                a * (backdrop[i] + (2 * source[i] - 1) * (d - backdrop[i]))
                + b * backdrop[i]
            )


def _blend_nop(
    source: Sequence[float], backdrop: MutableSequence[float], a: float, b: float
) -> None:
    pass


_blend_funcs: List[
    Callable[[Sequence[float], MutableSequence[float], float, float], None]
] = [
    _blend_nop,
    _blend_normal,
    _blend_multiply,
    _blend_screen,
    _blend_darken,
    _blend_lighten,
    _blend_overlay,
    _blend_soft_light,
    _blend_hard_light,
]


if len(_blend_funcs) != len(BlendMode) + 1:
    raise RuntimeError("one or more blend modes are unimplemented")


def blend_in_place(
    source: Sequence[float],
    backdrop: MutableSequence[float],
    mode: BlendMode = BlendMode.NORMAL,
) -> None:
    """Blends two colors according to standard alpha compositing rules, using
    the given blending mode and updating the second color in-place.
    """
    alpha_source = source[3]

    if alpha_source <= 0:
        # Shortcut for fully transparent source
        return

    # Apply the blending mode to the RGB part of the source and the backdrop

    if alpha_source >= 1 and mode is BlendMode.NORMAL:
        # Shortcut for the common case when the source is opaque and the
        # mode is NORMAL
        backdrop[:] = source
        return

    alpha_backdrop = backdrop[3]

    if alpha_backdrop >= 1:
        alpha_overlay = 1
        a = alpha_source
    else:
        alpha_overlay = 1 - (1 - alpha_source) * (1 - alpha_backdrop)
        a = alpha_source / alpha_overlay

    blend = _blend_funcs[mode]
    blend(source, backdrop, a, 1 - a)
    backdrop[3] = alpha_overlay
