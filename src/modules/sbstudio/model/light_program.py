from collections.abc import Iterable, Sequence
from operator import attrgetter
from typing import TypeVar

from sbstudio.utils import simplify_path

from .color import Color4D

__all__ = ("LightProgram",)

C = TypeVar("C", bound="LightProgram")


def _simplify_color_distance_func(
    keypoints: Iterable[Color4D], start: Color4D, end: Color4D
):
    """Distance function for LightProgram.simplify()"""
    timespan = end.t - start.t

    result: list[float] = []

    for point in keypoints:
        ratio = (point.t - start.t) / timespan if timespan > 0 else 0.5
        interp = (
            start.r + ratio * (end.r - start.r),
            start.g + ratio * (end.g - start.g),
            start.b + ratio * (end.b - start.b),
        )

        diff = max(
            abs(interp[0] - point.r),
            abs(interp[1] - point.g),
            abs(interp[2] - point.b),
        )
        result.append(diff)

    return result


def _simplify_color_eq_func(p1: Color4D, p2: Color4D):
    """Equality function for LightProgram.simplify()"""
    return p1.r == p2.r and p1.g == p2.g and p1.b == p2.b


class LightProgram:
    """Simplest representation of a causal light program in space and time.

    The color between given points is linearly interpolated or kept constant
    from past according to the is_fade property of each Color4D element.
    """

    def __init__(self, colors: Sequence[Color4D] | None = None):
        self.colors = sorted(colors, key=attrgetter("t")) if colors is not None else []

    def append(self, color: Color4D) -> None:
        """Add a color to the end of the light program."""
        if self.colors and self.colors[-1].t > color.t:
            raise ValueError(
                "New color must come after existing light keyframe in time"
            )
        self.colors.append(color)

    def as_dict(self, ndigits: int = 3):
        """Create a Skybrush-compatible dictionary representation of this instance.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary to be converted to JSON later
        """
        return {
            "data": [
                [
                    round(color.t, ndigits=ndigits),
                    [int(color.r), int(color.g), int(color.b)],
                    1 if color.is_fade else 0,
                ]
                for color in self.colors
            ],
            "version": 1,
        }

    def shift_time_in_place(self: C, delta: float) -> C:
        """Shifts all timestamps of the light program in-place.

        Parameters:
            delta: the time delta to add to the timestamp of each keyframe in the
                light program.
        """
        for keyframe in self.colors:
            keyframe.t += delta
        return self

    def simplify(self) -> "LightProgram":
        """Simplifies the light code by removing unnecessary keypoints
        from it.

        Return:
            LightProgram instance with the simplified light code.

        """
        new_items = simplify_path(
            list(self.colors),
            eps=4,
            distance_func=_simplify_color_distance_func,
            eq_func=_simplify_color_eq_func,
        )

        return LightProgram(new_items)
