from collections.abc import MutableSequence
from typing import TypeAlias

__all__ = ("Coordinate3D", "RGBAColor", "Rotation3D")


Coordinate3D: TypeAlias = tuple[float, float, float]
"""Type alias for simple 3D coordinates."""

RGBAColor: TypeAlias = tuple[float, float, float, float]
"""Type alias for RGBA color tuples used by Blender."""

MutableRGBAColor: TypeAlias = MutableSequence[float]
"""Type alias for RGBA color components that can be mutated in-place."""

RGBAColorLike: TypeAlias = RGBAColor | MutableRGBAColor
"""Type alias for mutable or immutable RGBA colors."""

Rotation3D: TypeAlias = tuple[float, float, float]
"""Type alias for simple 3D rotations."""
