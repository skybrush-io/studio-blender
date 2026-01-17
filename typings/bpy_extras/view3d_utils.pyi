from typing import TypeAlias, TypeVar, overload

from bpy.types import Region, RegionView3D
from mathutils import Vector

T = TypeVar("T")

Coordinate: TypeAlias = tuple[float, float, float]

@overload
def location_3d_to_region_2d(
    region: Region, rv3d: RegionView3D, coord: Coordinate
) -> Vector | None: ...
@overload
def location_3d_to_region_2d(
    region: Region, rv3d: RegionView3D, coord: Coordinate, *, default: T
) -> Vector | T: ...
