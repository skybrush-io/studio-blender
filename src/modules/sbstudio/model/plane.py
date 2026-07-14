from collections.abc import Sequence
from dataclasses import dataclass

from numpy import array, bool_, float32, ndarray
from numpy.typing import ArrayLike, NDArray

from .types import Coordinate3D


@dataclass(frozen=True)
class Plane:
    """Class that specifies a plane in 3D space.

    The plane is defined as the set of points that satisfy the equation of the
    form ``a*x + b*y + c*z = d``, where `(a, b, c)` is the normal vector of the
    plane and `d` is the offset.
    """

    normal: NDArray[float32]
    """The normal vector of the plane, stored as a NumPy array of shape ``(3,)``."""

    offset: float
    """The offset parameter of the plane equation."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Plane):
            return NotImplemented
        return (self.normal == other.normal).all() and self.offset == other.offset

    def __hash__(self) -> int:
        return hash((tuple(map(float, self.normal)), self.offset))

    def __repr__(self) -> str:
        normal = f"({self.normal[0]}, {self.normal[1]}, {self.normal[2]})"
        return f"Plane(normal={normal}, offset={self.offset})"

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
    def from_normal_and_point(cls, normal: Sequence[float], point: Sequence[float]):
        """Constructs a plane from its normal vector and an arbitrary point
        on the plane.

        Args:
            normal: the normal vector
            point: the point on the plane
        """
        offset = point[0] * normal[0] + point[1] * normal[1] + point[2] * normal[2]
        return cls.from_normal_and_offset(normal, offset)

    @classmethod
    def from_normal_and_offset(cls, normal: ArrayLike, offset: float):
        """Constructs a plane from its normal vector and offset value.

        Args:
            normal: the normal vector
            point: the offset value
        """
        if not isinstance(normal, ndarray):
            normal_array = array(normal, dtype=float32)
        else:
            normal_array = normal.astype(float32)  # ty:ignore[no-matching-overload]
        return cls(normal_array, offset)

    def is_front(self, p: Coordinate3D) -> bool:
        """Returns whether the given point is on the front side of the plane.
        Points that lie exactly on the plane are considered to be on the front
        side.
        """
        return bool(self.normal @ p >= self.offset)

    def is_front_many(self, points: NDArray[float32], out: NDArray[bool_]) -> None:
        """Returns whether each point in the given array is on the front side
        of the plane.

        Args:
            points: a NumPy array of shape ``(n, 3)``, one coordinate per row
            out: a Boolean NumPy array of ``shape(n, )`` where the result will be
                written.
        """
        out[:] = points @ self.normal >= self.offset
