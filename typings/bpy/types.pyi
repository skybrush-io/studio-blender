from __future__ import annotations

from contextlib import AbstractContextManager
from typing import (
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

class bpy_prop_collection(Sequence[T]):
    def find(self, key: str) -> int: ...
    @overload
    def get(self, key: str) -> Optional[T]: ...
    @overload
    def get(self, key: str, default: U) -> Union[T, U]: ...
    def __getitem__(self, key: Union[int, str]) -> T: ...
    def __len__(self) -> int: ...

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

class Constraint(bpy_struct):
    name: str
    influence: float
    type: Literal[
        "CAMERA_SOLVER",
        "FOLLOW_TRACK",
        "OBJECT_SOLVER",
        "COPY_LOCATION",
        "COPY_ROTATION",
        "COPY_SCALE",
        "COPY_TRANSFORMS",
        "LIMIT_DISTANCE",
        "LIMIT_LOCATION",
        "LIMIT_ROTATION",
        "LIMIT_SCALE",
        "MAINTAIN_VOLUME",
        "TRANSFORM",
        "TRANSFORM_CACHE",
        "TRACK_TO",
        "DAMPED_TRACK",
        "IK",
        "LOCKED_TRACK",
        "SPLINE_IK",
        "STRETCH_TO",
        "TRACK_TO",
        "ACTION",
        "ARMATURE",
        "CHILD_OF",
        "FLOOR",
        "FOLLOW_PATH",
        "PIVOT",
        "SHRINKWRAP",
    ]

class CopyLocationConstraint(Constraint):
    target: Object
    subtarget: str

Self = TypeVar("Self", bound="ID")

class ID(bpy_struct):
    name: str
    users: int

    def copy(self: Self) -> Self: ...

class MeshVertex(bpy_struct):
    groups: bpy_prop_collection[VertexGroupElement]
    index: int
    select: bool

class PropertyGroup(bpy_struct):
    name: str

class RenderSettings(bpy_struct):
    fps: int
    fps_base: float

class VertexGroup(bpy_struct):
    index: int
    lock_weight: bool
    name: str

    def add(
        self, index: int, weight: float, type: Literal["ADD", "REPLACE", "SUBTRACT"]
    ) -> None: ...
    def remove(self, index: int) -> None: ...
    def weight(self, index: int) -> float: ...

class VertexGroupElement(bpy_struct):
    group: int
    weight: float

class VertexGroups(bpy_prop_collection[VertexGroup]): ...
class ViewLayer(bpy_struct): ...

class Collection(ID):
    children: CollectionChildren
    objects: CollectionObjects

class Image(ID):
    depth: int
    frame_duration: int
    size: tuple[int, int]
    pixels: Sequence[float]

class Material(ID): ...

class Mesh(ID):
    vertices: bpy_prop_collection[MeshVertex]

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

    collection: Collection
    eevee: SceneEEVEE
    render: RenderSettings
    skybrush: DroneShowAddonProperties

    def frame_set(self, frame: int, subframe: float = 0.0) -> None: ...

class SceneEEVEE(bpy_struct):
    bloom_radius: float  # only for Blender <4.3
    bloom_intensity: float  # only for Blender <4.3
    use_bloom: bool  # only for Blender <4.3

class Context(bpy_struct):
    area: Area
    scene: Scene
    space_data: Space

    def evaluated_depsgraph_get(self) -> Depsgraph: ...
    def temp_override(
        self, *, window=None, area=None, region=None, **kwds
    ) -> AbstractContextManager[None]: ...

class Object(ID):
    active_material: Material
    constraints: ObjectConstraints
    vertex_groups: VertexGroups

    data: ID
    location: Vector3
    scale: Vector3

    hide_render: bool
    hide_select: bool
    hide_viewport: bool

    matrix_basis: Matrix
    matrix_local: Matrix
    matrix_parent_inverse: Matrix
    matrix_world: Matrix

    def select_get(self, view_layer: Optional[ViewLayer] = None) -> bool: ...
    def select_set(
        self, state: bool, view_layer: Optional[ViewLayer] = None
    ) -> None: ...

class CollectionChildren(bpy_prop_collection[Collection]):
    def link(self, object: Object) -> None: ...
    def unlink(self, object: Object) -> None: ...

class CollectionObjects(bpy_prop_collection[Object]):
    def link(self, object: Object) -> None: ...
    def unlink(self, object: Object) -> None: ...

class ObjectConstraints(bpy_prop_collection[Constraint]):
    def new(self, type: str) -> Constraint: ...

class BlendDataCollections(bpy_prop_collection[Collection]):
    def new(self, name: str) -> Collection: ...
    def remove(
        self, collection: Collection, do_unlink=True, do_id_user=True, do_ui_user=True
    ) -> None: ...

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

class BlendDataObjects(bpy_prop_collection[Object]):
    def remove(
        self, object: Object, do_unlink=True, do_id_user=True, do_ui_user=True
    ) -> None: ...

class BlendData(bpy_struct):
    collections: BlendDataCollections
    images: BlendDataImage
    materials: bpy_prop_collection[Material]
    meshes: bpy_prop_collection[Mesh]
    objects: BlendDataObjects
    scenes: bpy_prop_collection[Scene]
    textures: BlendDataTextures
    version: tuple[int, int, int]

class Space(bpy_struct):
    show_locked_time: bool
    show_region_header: bool
    type: Literal[
        "EMPTY",
        "VIEW_3D",
        "IMAGE_EDITOR",
        "NODE_EDITOR",
        "SEQUENCE_EDITOR",
        "CLIP_EDITOR",
        "DOPESHEET_EDITOR",
        "GRAPH_EDITOR",
        "NLA_EDITOR",
        "TEXT_EDITOR",
        "CONSOLE",
        "INFO",
        "TOPBAR",
        "STATUSBAR",
        "OUTLINER",
        "PROPERTIES",
        "FILE_BROWSER",
        "SPREADSHEET",
        "PREFERENCES",
    ]

class Area(bpy_struct):
    regions: bpy_prop_collection[Region]
    height: int
    width: int

    def tag_redraw(self) -> None: ...

class Region(bpy_struct):
    x: int
    y: int
    width: int
    height: int

class SpaceView3D(Space):
    overlay: View3DOverlay
    shading: View3DShading

class View3DOverlay(bpy_struct):
    show_overlays: bool

class View3DShading(bpy_struct):
    type: Literal["WIREFRAME", "SOLID", "MATERIAL", "RENDERED"]
