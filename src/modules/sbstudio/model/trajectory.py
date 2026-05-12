from base64 import b64encode
from collections.abc import Sequence
from itertools import chain
from operator import attrgetter
from typing import Self

from numpy import arange, array, interp

from .point import Point3D, Point4D

__all__ = ("Trajectory",)


class Trajectory:
    """Simplest representation of a causal trajectory in space and time.

    Positions between given Point4D elements are assumed to be
    linearly interpolated both in space and time.
    """

    def __init__(self, points: Sequence[Point4D] = []):
        self.points = sorted(points, key=attrgetter("t"))

    @property
    def first_point(self) -> Point4D | None:
        return self.points[0] if self.points else None

    @property
    def first_time(self) -> float | None:
        return self.points[0].t if self.points else None

    @property
    def last_point(self) -> Point4D | None:
        return self.points[-1] if self.points else None

    @property
    def last_time(self) -> float | None:
        return self.points[-1].t if self.points else None

    def append(self, point: Point4D) -> None:
        """Add a point to the end of the trajectory."""
        if self.points and self.points[-1].t >= point.t:
            raise ValueError("New point must come after existing trajectory in time")
        self.points.append(point)

    def as_dict(self, ndigits: int = 3, *, version: int = 2):
        """Create a Skybrush-compatible dictionary representation of this
        instance.

        Parameters:
            ndigits: round floats to this precision
            version: version of the representation to generate

        Return:
            dictionary of this instance, to be converted to JSON later

        """
        if version == 0:
            # Deprecated representation used in the past to send a trajectory for
            # rendering to .skyc into the Skybrush Studio server. This
            # representation indicates to the Skybrush Studio server that the
            # points are samples and it is allowed to simplify the trajectory
            # further by eliminating unneeded points.
            #
            # Use version 2 instead, which does the same but in a faster and
            # smaller binary representation
            return {
                "points": [
                    [
                        round(point.t, ndigits=ndigits),
                        round(point.x, ndigits=ndigits),
                        round(point.y, ndigits=ndigits),
                        round(point.z, ndigits=ndigits),
                    ]
                    for point in self.points
                ],
                "version": 0,
            }
        elif version == 1:
            # Standard representation
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
        elif version == 2:
            # Representation similar to version 0 but in a binary form for
            # reducing bandwidth usage and increasing render speed
            # TODO: use numpy arrays in Trajectory already for additional speedup
            floats = array(
                list(chain.from_iterable(point.as_tuple() for point in self.points)),
                dtype="<f4",
            )
            return {
                "points": b64encode(floats.tobytes()).decode("ascii"),
                "version": 2,
            }
        else:
            raise ValueError(f"Unknown version {version} for trajectory representation")

    @property
    def duration(self) -> float:
        """Returns the duration of the trajectory in seconds."""

        if len(self.points) < 2:
            return 0

        return self.points[-1].t - self.points[0].t

    def resample_in_place(self, fps: float) -> Self:
        """Resamples the trajectory to the given FPS value in-place.

        Parameters:
            fps: the new fps value to resample the trajectories to, in [1/s]

        """

        if not self.points:
            return self
        assert self.first_time is not None
        assert self.last_time is not None

        source_times = [p.t for p in self.points]
        target_times = arange(self.first_time, self.last_time, 1 / fps)

        resampled_x = interp(target_times, source_times, [p.x for p in self.points])
        resampled_y = interp(target_times, source_times, [p.y for p in self.points])
        resampled_z = interp(target_times, source_times, [p.z for p in self.points])

        self.points = [
            Point4D(t, x, y, z)
            for t, x, y, z in zip(target_times, resampled_x, resampled_y, resampled_z)
        ]

        return self

    def shift_in_place(self, offset: Point3D) -> Self:
        """Shifts all points of the trajectory in-place.

        Parameters:
            offset: the spatial offset to add to each point in the
                trajectory.
        """
        for point in self.points:
            point.x += offset.x
            point.y += offset.y
            point.z += offset.z
        return self

    def shift_time_in_place(self, delta: float) -> Self:
        """Shifts all timestamp of the trajectory in-place.

        Parameters:
            delta: the time delta to add to the timestamp of each point in the
                trajectory.
        """
        for point in self.points:
            point.t += delta
        return self

    def simplify_in_place(self) -> Self:
        """Simplifies the trajectory in-place by removing points that are
        identical to their predecessors and successors.
        """
        if not self.points:
            return self

        first_point = self.points[0]
        new_points: list[Point4D] = []

        # Make up a fake last point that is different from the first one
        last_point = Point4D(
            t=first_point.t - 1,
            x=first_point.x - 1,
            y=first_point.y - 1,
            z=first_point.z - 1,
        )

        keep_next = False
        for point in self.points:
            prev_is_same = (
                last_point.x == point.x
                and last_point.y == point.y
                and last_point.z == point.z
            )
            if keep_next or not prev_is_same:
                new_points.append(point)
            else:
                new_points[-1] = point
            keep_next = not prev_is_same
            last_point = point

        self.points = new_points
        return self
