import sys

from typing import Union

from bmesh.types import BMesh
from bpy.types import Depsgraph, Mesh
from mathutils import Vector

class BVHTree:
    @classmethod
    def FromBMesh(cls, bmesh: BMesh, epsilon: float = 0.0): ...
    @classmethod
    def FromObject(
        cls,
        object: Mesh,
        depsgraph: Depsgraph,
        deform: bool = True,
        render: bool = False,
        cage: bool = False,
        epsilon: float = 0.0,
    ): ...
    def ray_cast(
        self,
        origin: Union[Vector, tuple[float, ...]],
        direction: Union[Vector, tuple[float, ...]],
        distance: float = sys.float_info.max,
    ) -> tuple[Vector, Vector, int, float]: ...
