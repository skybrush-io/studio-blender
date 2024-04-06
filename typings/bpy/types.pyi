from typing import Generic, Optional, TypeVar, Union, overload

from mathutils import Matrix
from sbstudio.plugin.model import DroneShowAddonProperties

T = TypeVar("T")
U = TypeVar("U")

Vector3 = tuple[float, float, float]

class bpy_prop_collection(Generic[T]):
    def find(self, key: str) -> int: ...
    @overload
    def get(self, key: str) -> Optional[T]: ...
    @overload
    def get(self, key: str, default: U) -> Union[T, U]: ...

class bpy_struct: ...

Self = TypeVar("Self", bound="ID")

class ID(bpy_struct):
    name: str

    def copy(self: Self) -> Self: ...

class Mesh(ID):
    def transform(self, matrix: Matrix, shape_keys: bool = False) -> None: ...

class Depsgraph(bpy_struct):
    objects: bpy_prop_collection[Object]
    scene: Scene
    scene_eval: Scene

class Scene:
    skybrush: DroneShowAddonProperties

class Context(bpy_struct):
    scene: Scene

    def evaluated_depsgraph_get(self) -> Depsgraph: ...

class Object(ID):
    data: ID
    location: Vector3
    scale: Vector3

    matrix_basis: Matrix
    matrix_local: Matrix
    matrix_parent_inverse: Matrix
    matrix_world: Matrix
