from operator import attrgetter
from typing import Sequence

from .point import Point4D

__all__ = ("Trajectory",)


class Trajectory:
    """Simplest representation of a causal trajectory in space and time.

    Positions between given Point4D elements are assumed to be
    linearly interpolated both in space and time.

    """

    def __init__(self, points: Sequence[Point4D] = []):
        self.points = sorted(points, key=attrgetter("t"))

    def append(self, point: Point4D) -> None:
        """Add a point to the end of the trajectory."""
        if self.points and self.points[-1].t >= point.t:
            raise ValueError("New point must come after existing trajectory in time")
        self.points.append(point)

    def as_dict(self, ndigits: int = 3):
        """Create a Skybrush-compatible dictionary representation of self.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary of self to be converted to SJON later

        """
        return {
            "points": [
                [
                    round(point.t, ndigits=ndigits),
                    [
                        round(point.x, ndigits=ndigits),
                        round(point.y, ndigits=ndigits),
                        round(point.z, ndigits=ndigits),
                    ],
                    [],
                ]
                for point in self.points
            ],
            "version": 1,
        }
