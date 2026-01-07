from collections.abs import MutableSequence

__all__ = ("Coordinate3D", "RGBAColor", "Rotation3D")


#: Type alias for simple 3D coordinates
Coordinate3D = tuple[float, float, float]

#: Type alias for RGBA color tuples used by Blender
RGBAColor = tuple[float, float, float, float]

#: Type alias for RGBA color components that can be mutated in-place
MutableRGBAColor = MutableSequence[float]

#: Type alias for mutable or immutable RGBA colors
RGBAColorLike = RGBAColor | MutableRGBAColor

#: Type alias for simple 3D rotations
Rotation3D = tuple[float, float, float]
