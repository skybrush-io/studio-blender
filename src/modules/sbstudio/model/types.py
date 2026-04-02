from collections.abc import MutableSequence
from typing import TypeAlias

__all__ = ("Coordinate3D", "RGBAColor", "Rotation3D")


Coordinate3D: TypeAlias = tuple[float, float, float]
"""Type alias for simple 3D coordinates."""

RGBColor: TypeAlias = tuple[float, float, float]
"""Type alias for RGB color tuples used by Blender."""

MutableRGBColor: TypeAlias = MutableSequence[float]
"""Type alias for RGB color components that can be mutated in-place."""

RGBColorLike: TypeAlias = RGBColor | MutableRGBColor
"""Type alias for mutable or immutable RGB colors."""

RGBAColor: TypeAlias = tuple[float, float, float, float]
"""Type alias for RGBA color tuples used by Blender."""

MutableRGBAColor: TypeAlias = MutableSequence[float]
"""Type alias for RGBA color components that can be mutated in-place."""

RGBAColorLike: TypeAlias = RGBAColor | MutableRGBAColor
"""Type alias for mutable or immutable RGBA colors."""

Color: TypeAlias = RGBColor | RGBAColor
"""Type alias for immutable colors, either RGB or RGBA."""

ColorLike: TypeAlias = RGBColorLike | RGBAColorLike
"""Type alias for mutable or immutable colors, either RGB or RGBA."""

Rotation3D: TypeAlias = tuple[float, float, float]
"""Type alias for simple 3D rotations."""

Quaternion: TypeAlias = tuple[float, float, float, float]
"""Type alias for 4D quaternions."""
