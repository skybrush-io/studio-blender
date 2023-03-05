from typing import Tuple

__all__ = ("Coordinate3D", "RGBAColor")


#: Type alias for simple 3D coordinates
Coordinate3D = Tuple[float, float, float]

#: Type alias for simple 3D coordinates of a line segment
LineSegment3D = Tuple[Coordinate3D, Coordinate3D]

#: Type alias for RGBA color tuples used by Blender
RGBAColor = Tuple[float, float, float, float]
