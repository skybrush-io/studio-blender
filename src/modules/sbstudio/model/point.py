from dataclasses import dataclass
from mathutils import Vector

__all__ = ("Point3D", "Point4D")


@dataclass
class Point3D:
    """Simplest representation of a 3D point in space."""

    # x coordinate in [m]
    x: float

    # y coordinate in [m]
    y: float

    # z coordinate in [m]
    z: float

    def at_time(self, t: float) -> "Point4D":
        """Returns a Point4D copy of this point such that the copy is placed
        at the given number of seconds on the time axis.

        Parameters:
            t: the number of seconds where the new point should be placed
                on the time axis
        Returns:
            Point4D: the constructed 4D point
        """
        return Point4D(t=t, x=self.x, y=self.y, z=self.z)

    def as_vector(self) -> Vector:
        """Returns a Point3D instance as a Blender Vector."""
        return Vector((self.x, self.y, self.z))


@dataclass
class Point4D:
    """Simplest representation of a 4D point in space and time."""

    # time in [s]
    t: float

    # x coordinate in [m]
    x: float

    # y coordinate in [m]
    y: float

    # z coordinate in [m]
    z: float

    def as_3d(self) -> Point3D:
        """Returns a Point3D instance that is at the same coordinates as this
        instance.

        Returns:
            a Point3D instance that is at the same coordinates as this
                instance
        """
        return Point3D(x=self.x, y=self.y, z=self.z)
