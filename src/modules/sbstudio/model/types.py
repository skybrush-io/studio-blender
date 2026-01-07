from collections.abc import MutableSequence
from typing import TypeAlias

__all__ = ("Coordinate3D", "RGBAColor", "Rotation3D")


#: Type alias for simple 3D coordinates
Coordinate3D: TypeAlias = tuple[float, float, float]

#: Type alias for RGBA color tuples used by Blender
RGBAColor: TypeAlias = tuple[float, float, float, float]

#: Type alias for RGBA color components that can be mutated in-place
MutableRGBAColor: TypeAlias = MutableSequence[float]

#: Type alias for mutable or immutable RGBA colors
RGBAColorLike: TypeAlias = RGBAColor | MutableRGBAColor

#: Type alias for simple 3D rotations
Rotation3D: TypeAlias = tuple[float, float, float]
