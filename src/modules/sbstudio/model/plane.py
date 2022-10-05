from dataclasses import dataclass

from .types import Coordinate3D


@dataclass(frozen=True)
class Plane:
    """Class that specifies a plane in 3D space.

    The plane is defined as the set of points that satisfy the equation of the
    form ``a*x + b*y + c*z = d``, where `(a, b, c)` is the normal vector of the
    plane and `d` is the offset.
    """

    normal: Coordinate3D
    """The normal vector of the plane."""

    offset: float
    """The offset parameter of the plane equation."""

    @classmethod
    def from_points(cls, p: Coordinate3D, q: Coordinate3D, r: Coordinate3D):
        """Constructs a plane from three points.

        Args:
            p: the first point
            q: the second point
            r: the third point

        Raises:
            RuntimeError: if the three points are collinear
        """
        pq = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        pr = r[0] - p[0], r[1] - p[1], r[2] - p[2]
        normal = (
            pq[1] * pr[2] - pq[2] * pr[1],
            pq[0] * pr[2] - pq[2] * pr[0],
            pq[0] * pr[1] - pq[1] * pr[0],
        )
        if all(x == 0 for x in normal):
            raise RuntimeError("The given points are collinear")

        return cls.from_normal_and_point(normal, p)

    @classmethod
    def from_normal_and_point(cls, normal: Coordinate3D, point: Coordinate3D):
        """Constructs a plane from its normal vector and an arbitrary point
        on the plane.

        Args:
            normal: the normal vector
            point: the point on the plane
        """
        offset = point[0] * normal[0] + point[1] * normal[1] + point[2] * normal[2]
        return cls(normal, offset)

    def is_front(self, p: Coordinate3D) -> bool:
        """Returns whether the given point is on the front side of the plane.
        Points that lie exactly on the plane are considered to be on the front
        side.
        """
        x = self.normal[0] * p[0] + self.normal[1] * p[1] + self.normal[2] * p[2]
        return x >= self.offset
