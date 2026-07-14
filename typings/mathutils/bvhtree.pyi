import sys

from bmesh.types import BMesh
from bpy.types import Depsgraph, Object
from mathutils import Vector

class BVHTree:
    @classmethod
    def FromBMesh(cls, bmesh: BMesh, epsilon: float = 0.0) -> BVHTree: ...
    @classmethod
    def FromObject(
        cls,
        object: Object,
        depsgraph: Depsgraph,
        deform: bool = True,
        render: bool = False,
        cage: bool = False,
        epsilon: float = 0.0,
    ) -> BVHTree: ...
    def find_nearest(
        self, origin: Vector | tuple[float, ...], distance: float = 1.84467e19, /
    ) -> tuple[Vector, Vector, int, float]: ...
    def ray_cast(
        self,
        origin: Vector | tuple[float, ...],
        direction: Vector | tuple[float, ...],
        distance: float = sys.float_info.max,
        /,
    ) -> tuple[Vector | None, Vector | None, int | None, float | None]: ...
