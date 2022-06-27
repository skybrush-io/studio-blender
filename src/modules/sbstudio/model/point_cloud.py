from typing import List, Union

from .point import Point3D, Point4D

__all__ = ("PointCloud",)


class PointCloud:
    """Simplest representation of a list/group/cloud of Point3D points."""

    def __init__(self, points: List[Union[Point3D, Point4D]] = []):
        self._points = [Point3D(x=p.x, y=p.y, z=p.z) for p in points]

    def __getitem__(self, item):
        return self._points[item]

    def append(self, point: Union[Point3D, Point4D]) -> None:
        """Add a point to the end of the point cloud."""
        self._points.append(Point3D(x=point.x, y=point.y, z=point.z))

    def as_list(self, ndigits: int = 3):
        """Create a Skybrush-compatible list representation of this instance.

        Parameters:
            ndigits: round floats to this precision

        Return:
            list representation of this instance, to be converted to JSON later

        """
        return [
            [
                round(point.x, ndigits=ndigits),
                round(point.y, ndigits=ndigits),
                round(point.z, ndigits=ndigits),
            ]
            for point in self._points
        ]

    @property
    def count(self):
        """Return the number of points."""
        return len(self._points)
