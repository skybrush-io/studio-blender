from dataclasses import dataclass
from mathutils import Vector

__all__ = (
    "Color3D",
    "Color4D",
)


@dataclass
class Color3D:
    """Simplest representation of a 3D color in RGB space."""

    #: red component of the color in the range [0-255]
    r: int

    #: green component of the color in the range [0-255]
    g: int

    #: blue component of the color in the range [0-255]
    b: int

    def at_time(self, t: float, is_fade: bool = True) -> "Color4D":
        """Returns a Color4D copy of this color such that the copy is placed
        at the given number of seconds on the time axis.

        Parameters:
            t: the number of seconds where the new color should be placed
                on the time axis
            is_fade: flag to specify whether we should fade here from the
                previous keypoint (True) or maintain previous color until this
                moment and change here abruptly (False)
        Returns:
            Color4D: the constructed 4D color
        """
        return Color4D(t=t, r=self.r, g=self.g, b=self.b, is_fade=is_fade)

    def as_vector(self) -> Vector:
        """Converts a Color3D instance to a Blender color vector with alpha
        channel included."""
        return Vector((self.r / 255, self.g / 255, self.b / 255, 1))


@dataclass
class Color4D:
    """Simplest representation of a 4D color in RGB space and time."""

    #: time in [s]
    t: float

    #: red component of the color in the range [0-255]
    r: int

    #: green component of the color in the range[0-255]
    g: int

    #: blue component of the color in the range[0-255]
    b: int

    #: flag to specify whether we should fade here from the previous keypoint
    #: (True) or maintain previous color until this moment and change here
    #: abruptly (False)
    is_fade: bool = True

    def as_vector(self) -> Vector:
        """Converts a Color4D instance to a Blender color vector with alpha
        channel included and ignoring the timestamp."""
        return Vector((self.r / 255, self.g / 255, self.b / 255, 1))
