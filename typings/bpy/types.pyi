from __future__ import annotations

from typing import (
    Generic,
    Literal,
    MutableSequence,
    Optional,
    Sequence,
    TypeVar,
    Union,
    overload,
)

from mathutils import Matrix
from sbstudio.plugin.model import DroneShowAddonProperties

T = TypeVar("T")
U = TypeVar("U")

RGBAColor = MutableSequence[float]
Vector3 = tuple[float, float, float]

class bpy_prop_collection(Generic[T], Sequence[T]):
    def find(self, key: str) -> int: ...
    @overload
    def get(self, key: str) -> Optional[T]: ...
    @overload
    def get(self, key: str, default: U) -> Union[T, U]: ...

class bpy_struct: ...

class ColorRampElement(bpy_struct):
    alpha: float
    color: RGBAColor
    position: float

class ColorRamp(bpy_struct):
    color_mode: Literal["RGB", "HSV", "HSL"]
    elements: bpy_prop_collection[ColorRampElement]
    hue_interpolation: Literal["NEAR", "FAR", "CW", "CCW"]
    interpolation: Literal["EASE", "CARDINAL", "LINEAR", "B_SPLINE", "CONSTANT"]

    def evaluate(self, position: float) -> RGBAColor: ...

Self = TypeVar("Self", bound="ID")

class ID(bpy_struct):
    name: str

    def copy(self: Self) -> Self: ...

class PropertyGroup(bpy_struct):
    name: str

class RenderSettings(bpy_struct):
    fps: int
    fps_base: float

class Image(ID):
    depth: int
    size: tuple[int, int]

class Material(ID): ...

class Mesh(ID):
    def transform(self, matrix: Matrix, shape_keys: bool = False) -> None: ...

class Texture(ID):
    color_ramp: ColorRamp
    use_color_ramp: bool

class ImageTexture(Texture):
    image: Optional[Image]

class Depsgraph(bpy_struct):
    objects: bpy_prop_collection[Object]
    scene: Scene
    scene_eval: Scene

class Scene:
    frame_current: int
    frame_current_final: float
    frame_end: int
    frame_float: float
    frame_preview_end: int
    frame_preview_start: int
    frame_start: int
    frame_step: int
    frame_subframe: float

    render: RenderSettings
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

class BlendDataImage(bpy_prop_collection[Image]):
    def new(
        self,
        name: str,
        width: int,
        height: int,
        alpha=False,
        float_buffer=False,
        stereo3d=False,
        is_data=False,
        tiled=False,
    ) -> Image: ...

class BlendDataTextures(bpy_prop_collection[Texture]):
    @overload
    def new(self, name: str, type: Literal["IMAGE"]) -> ImageTexture: ...
    @overload
    def new(self, name: str, type: str) -> Texture: ...

class BlendData(bpy_struct):
    images: BlendDataImage
    materials: bpy_prop_collection[Material]
    meshes: bpy_prop_collection[Mesh]
    objects: bpy_prop_collection[Object]
    scenes: bpy_prop_collection[Scene]
    textures: BlendDataTextures
    version: tuple[int, int, int]