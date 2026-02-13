from __future__ import annotations

from collections.abc import Callable, MutableSequence, Sequence
from contextlib import AbstractContextManager
from typing import Any, Iterable, Literal, TypeAlias, TypeVar, overload

from mathutils import Matrix, Vector
from sbstudio.plugin.model import (
    DroneShowAddonObjectProperties,
    DroneShowAddonProperties,
)

T = TypeVar("T")
U = TypeVar("U")

IdType: TypeAlias = Literal[
    "ACTION",
    "ARMATURE",
    "BRUSH",
    "CACHEFILE",
    "CAMERA",
    "COLLECTION",
    "CURVE",
    "CURVES",
    "FONT",
    "GREASEPENCIL",
    "GREASEPENCIL_V3",
    "IMAGE",
    "KEY",
    "LATTICE",
    "LIBRARY",
    "LIGHT",
    "LIGHT_PROBE",
    "LINESTYLE",
    "MASK",
    "MATERIAL",
    "MESH",
    "META",
    "MOVIECLIP",
    "NODETREE",
    "OBJECT",
    "PAINTCURVE",
    "PALETTE",
    "PARTICLE",
    "POINTCLOUD",
    "SCENE",
    "SCREEN",
    "SOUND",
    "SPEAKER",
    "TEXT",
    "TEXTURE",
    "VOLUME",
    "WINDOWMANAGER",
    "WORKSPACE",
    "WORLD",
]

EmptyDisplayType: TypeAlias = Literal[
    "PLAIN_AXES", "ARROWS", "SINGLE_ARROW", "CIRCLE", "CUBE", "SPHERE", "CONE", "IMAGE"
]

RGBAColor = MutableSequence[float]
Vector3 = tuple[float, float, float]

class bpy_prop_collection(Sequence[T]):
    def find(self, key: str) -> int: ...
    @overload
    def foreach_get(self, attr: str, seq: Sequence[float]) -> None: ...
    @overload
    def foreach_get(self, attr: str, seq: Sequence[bool]) -> None: ...
    @overload
    def foreach_set(self, attr: str, seq: Sequence[float]) -> None: ...
    @overload
    def foreach_set(self, attr: str, seq: Sequence[bool]) -> None: ...
    @overload
    def get(self, key: str) -> T | None: ...
    @overload
    def get(self, key: str, default: U) -> T | U: ...
    def items(self) -> Iterable[tuple[str, T]]: ...
    def keys(self) -> Iterable[str]: ...
    def values(self) -> Iterable[T]: ...
    def __getitem__(self, key: int | str) -> T: ...  # type: ignore[reportIncompatibleMethodOverride]
    def __len__(self) -> int: ...

class bpy_prop_collection_idprop(bpy_prop_collection[T]):
    def add(self) -> T: ...
    def clear() -> None: ...
    def move(self, src_index: int, dst_index: int) -> None: ...
    def remove(self, index: int) -> None: ...

class bpy_struct:
    def keyframe_delete(
        self,
        data_path: str,
        /,
        *,
        index: int = -1,
        frame: float | None,
        group: str = "",
    ) -> bool: ...
    def keyframe_insert(
        self,
        data_path: str,
        /,
        *,
        index: int = -1,
        frame: float | None,
        group: str = "",
        options: set[
            Literal[
                "INSERTKEY_NEEDED",
                "INSERTKEY_VISUAL",
                "INSERTKEY_REPLACE",
                "INSERTKEY_AVAILABLE",
                "INSERTKEY_CYCLE_AWARE",
            ]
        ] = set(),
        keytype: Literal[
            "KEYFRAME", "BREAKDOWN", "MOVING_HOLD", "EXTREME", "JITTER", "GENERATED"
        ] = "KEYFRAME",
    ) -> bool: ...
    def keys(self) -> Iterable: ...
    def path_resolve(self, path: str): ...
    def values(self) -> Iterable: ...

class AnimData(bpy_struct):
    action: Action | None
    action_slot: ActionSlot | None

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

###############################################################################
## bpy_struct and ID subclasses

class ID(bpy_struct):
    name: str
    users: int
    id_type: IdType
    use_fake_user: bool

    def animation_data_create(self) -> AnimData | None: ...
    def copy(self: Self) -> Self: ...

class ActionChannelbag(bpy_struct):
    fcurves: ActionChannelbagFCurves
    slot: ActionSlot

class ActionKeyframeStrip(ActionStrip):
    channelbags: ActionChannelbags
    def channelbag(
        self, slot: ActionSlot, *, ensure: bool = False
    ) -> ActionChannelbag: ...

class ActionLayer(bpy_struct):
    name: str
    strips: ActionStrips

class ActionSlot(bpy_struct):
    active: bool
    handle: int
    identifier: str
    name_display: str
    select: bool
    show_expanded: bool

    def duplicate(self) -> ActionSlot: ...

ActionStripType = Literal["KEYFRAME"]

class ActionStrip(bpy_struct):
    type: ActionStripType

class Addon(bpy_struct):
    module: str
    preferences: AddonPreferences

class AddonPreferences(bpy_struct):
    layout: UILayout

class Attribute(bpy_struct): ...
class AttributeGroupPointCloud(bpy_prop_collection[Attribute]): ...

class FCurve(bpy_struct):
    array_index: int
    data_path: str
    keyframe_points: FCurveKeyframePoints
    lock: bool
    mute: bool
    select: bool

    def update(self) -> None: ...

class IDMaterials(bpy_struct):
    def append(self, material: Material) -> None: ...
    def clear(self) -> None: ...
    def pop(self, *, index: int = -1) -> Material: ...

KeyframeHandleType = Literal["FREE", "ALIGNED", "VECTOR", "AUTO", "AUTO_CLAMPED"]

class Keyframe(bpy_struct):
    co: Vector
    handle_left: Vector
    handle_left_type: KeyframeHandleType
    handle_right: Vector
    handle_right_type: KeyframeHandleType
    interpolation: Literal[
        "CONSTANT",
        "LINEAR",
        "BEZIER",
    ]

class MeshVertex(bpy_struct):
    co: Vector
    groups: bpy_prop_collection[VertexGroupElement]
    index: int
    select: bool

class Point(bpy_struct):
    co: Vector
    index: int
    radius: float

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

class Action(ID):
    layers: ActionLayers
    slots: ActionSlots

    def fcurve_ensure_for_datablock(
        self, datablock: ID, data_path: str, *, index: int = 0, group_name: str = ""
    ) -> FCurve: ...

class Collection(ID):
    children: CollectionChildren
    objects: CollectionObjects

    def link(self, obj: Object) -> None: ...
    def unlink(self, obj: Object) -> None: ...
    def remove(self, obj: Object) -> None: ...

class ColorManagedInputColorspaceSettings(ID):
    is_data: bool
    name: str

class Image(ID):
    depth: int
    frame_duration: int
    size: tuple[int, int]
    pixels: Sequence[float]
    colorspace_settings: ColorManagedInputColorspaceSettings

    def pack(self) -> None: ...

class Material(ID):
    node_tree: NodeTree

class MaterialSlot(bpy_struct):
    material: Material | None

class Mesh(ID):
    vertices: bpy_prop_collection[MeshVertex]

    def transform(self, matrix: Matrix, shape_keys: bool = False) -> None: ...

class NodeTree(ID):
    nodes: bpy_prop_collection[Node]
    links: bpy_prop_collection[NodeLink]
    animation_data: AnimationData | None

class Node(bpy_struct):
    inputs: bpy_prop_collection[NodeSocket]
    outputs: bpy_prop_collection[NodeSocket]
    name: str

class NodeLink(bpy_struct):
    from_node: Node
    to_node: Node
    from_socket: NodeSocket
    to_socket: NodeSocket

class NodeSocket(bpy_struct):
    name: str

class AnimationData(bpy_struct):
    action: Action | None
    drivers: bpy_prop_collection[FCurve]

class PointCloud(ID):
    anim_data: AnimData
    attributes: AttributeGroupPointCloud
    color_attributes: AttributeGroupPointCloud
    materials: IDMaterials
    points: bpy_prop_collection[Point]

class Texture(ID):
    color_ramp: ColorRamp
    use_color_ramp: bool

class ImageTexture(Texture):
    image: Image | None

class Depsgraph(bpy_struct):
    objects: bpy_prop_collection[Object]
    scene: Scene
    scene_eval: Scene

class Event(bpy_struct): ...

class Operator(bpy_struct):
    bl_idname: str
    bl_label: str
    bl_description: str
    layout: UILayout

    def report(
        self,
        type: set[
            Literal[
                "DEBUG",
                "INFO",
                "OPERATOR",
                "PROPERTY",
                "WARNING",
                "ERROR",
                "ERROR_INVALID_INPUT",
                "ERROR_INVALID_CONTEXT",
                "ERROR_OUT_OF_MEMORY",
            ]
        ],
        message: str,
    ) -> None: ...

class Particle(ID):
    name: str
    settings: ParticleSettings
    seed: int

class ParticleSettings(bpy_struct):
    type: str
    count: int
    frame_start: int
    frame_end: int
    lifetime: int
    emit_from: str
    use_emit_random: bool
    brownian_factor: float
    render_type: str

class ParticleSystem(bpy_struct):
    name: str
    seed: int
    settings: ParticleSettings

class Preferences(bpy_struct):
    addons: bpy_prop_collection[Addon]
    system: System

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
    cursor: View3DCursor
    eevee: SceneEEVEE
    objects: bpy_prop_collection[Object]
    render: RenderSettings
    skybrush: DroneShowAddonProperties
    timeline_markers: bpy_prop_collection[TimelineMarker]

    def frame_set(self, frame: int, subframe: float = 0.0) -> None: ...

class Screen: ...

class SceneEEVEE(bpy_struct):
    bloom_radius: float  # only for Blender <4.3
    bloom_intensity: float  # only for Blender <4.3
    use_bloom: bool  # only for Blender <4.3

class System(bpy_struct):
    ui_scale: float

class TextLine(bpy_struct):
    body: str

class TimelineMarker(bpy_struct):
    name: str
    frame: int
    select: bool
    camera: Object | None

class ToolSettings(bpy_struct):
    mesh_select_mode: list[bool]

class View3DCursor(bpy_struct):
    location: Vector
    matrix: Matrix

class WindowManager(ID):
    def fileselect_add(self, operator: Operator) -> None: ...
    def invoke_confirm(
        self,
        operator: Operator,
        event: Event,
        *,
        title: str = "",
        message: str = "",
        confirm_text: str = "",
        icon: str = "",
        text_ctxt: str = "",
        translate: bool = True,
    ) -> None: ...
    def invoke_props_dialog(
        self,
        operator: Operator,
        width: int = 0,
    ) -> None: ...

class Context(bpy_struct):
    area: Area
    active_object: Object
    mode: str
    object: Object
    preferences: Preferences
    region: Region
    region_data: RegionView3D
    region_popup: Region
    scene: Scene
    screen: Screen
    selected_objects: list[Object]
    space_data: Space
    tool_settings: ToolSettings
    window_manager: WindowManager

    def copy(self) -> Context: ...
    def evaluated_depsgraph_get(self) -> Depsgraph: ...
    def temp_override(
        self, *, window=None, area=None, region=None, **kwds
    ) -> AbstractContextManager[None]: ...

class Object(ID):
    active_material: Material
    animation_data: AnimData | None
    bound_box: tuple[tuple[float, float, float], ...]
    color: RGBAColor
    constraints: ObjectConstraints
    mode: str
    type: str
    vertex_groups: VertexGroups

    data: ID
    location: Vector3
    scale: Vector3

    empty_display_size: float
    empty_display_type: EmptyDisplayType

    hide_render: bool
    hide_select: bool
    hide_viewport: bool

    material_slots: bpy_prop_collection[MaterialSlot]

    matrix_basis: Matrix
    matrix_local: Matrix
    matrix_parent_inverse: Matrix
    matrix_world: Matrix

    modifiers: bpy_prop_collection[Modifier]

    particle_systems: list[ParticleSystem]

    skybrush: DroneShowAddonObjectProperties

    def evaluated_get(self, depsgraph: Depsgraph) -> Object: ...
    def select_get(self, view_layer: ViewLayer | None = None) -> bool: ...
    def select_set(self, state: bool, view_layer: ViewLayer | None = None) -> None: ...

class Modifier(bpy_struct):
    name: str
    type: str
    show_viewport: bool
    show_render: bool

###############################################################################
## Collection types

class ActionChannelbags(bpy_prop_collection[ActionChannelbag]):
    def new(self, slot: ActionSlot) -> ActionChannelbag: ...
    def remove(self, channelbag: ActionChannelbag) -> None: ...

class ActionChannelbagFCurves(bpy_prop_collection[FCurve]):
    def clear(self) -> None: ...
    def ensure(
        self, data_path: str, *, index: int = 0, group_name: str = ""
    ) -> FCurve: ...
    def find(self, data_path: str, *, index: int = 0) -> FCurve | None: ...  # type: ignore[reportIncompatibleMethodOverride]
    def new(
        self, data_path: str, *, index: int = 0, group_name: str = ""
    ) -> FCurve: ...
    def new_from_fcurve(self, fcurve: FCurve, *, data_path: str = "") -> FCurve: ...
    def remove(self, fcurve: FCurve) -> None: ...

class ActionLayers(bpy_prop_collection[ActionLayer]):
    def new(self, name: str) -> ActionLayer: ...
    def remove(self, anim_layer: ActionLayer) -> None: ...

class ActionSlots(bpy_prop_collection[ActionSlot]):
    def new(self, id_type: IdType, name: str) -> ActionSlot: ...
    def remove(self, action_slot: ActionSlot) -> None: ...

class ActionStrips(bpy_prop_collection[ActionStrip]):
    def new(self, *, type: ActionStripType) -> ActionStrip: ...
    def remove(self, anim_strip: ActionStrip) -> None: ...

class CollectionChildren(bpy_prop_collection[Collection]):
    def link(self, object: Object) -> None: ...
    def unlink(self, object: Object) -> None: ...

class CollectionObjects(bpy_struct, bpy_prop_collection[Object]):
    def link(self, object: Object) -> None: ...
    def unlink(self, object: Object) -> None: ...

class FCurveKeyframePoints(bpy_prop_collection[Keyframe]):
    def clear(self) -> None: ...
    def deduplicate(self) -> None: ...
    def handles_recalc(self) -> None: ...
    def insert(
        self,
        frame: float,
        value: float,
        *,
        options: set[Literal["REPLACE", "NEEDED", "FAST"]] = {"REPLACE"},
    ) -> Keyframe: ...
    def remove(self, keyframe: Keyframe, *, fast: bool = False) -> None: ...
    def sort(self) -> None: ...

class ObjectConstraints(bpy_prop_collection[Constraint]):
    def clear(self) -> None: ...
    def move(self, from_index: int, to_index: int) -> None: ...
    def new(self, type: str) -> Constraint: ...
    def remove(self, constraint: Constraint) -> None: ...

class BlendDataActions(bpy_prop_collection[Action]):
    def new(self, name: str) -> Action: ...
    def remove(
        self,
        action: Action,
        *,
        do_unlink: bool = True,
        do_id_user: bool = True,
        do_ui_user: bool = True,
    ) -> None: ...

class BlendDataCollections(bpy_prop_collection[Collection]):
    def new(self, name: str) -> Collection: ...
    def remove(
        self,
        collection: Collection,
        *,
        do_unlink: bool = True,
        do_id_user: bool = True,
        do_ui_user: bool = True,
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
    def new(self, name: str, object_data: ID | None) -> Object: ...
    def remove(
        self, object: Object, do_unlink=True, do_id_user=True, do_ui_user=True
    ) -> None: ...

class BlendDataPointClouds(bpy_prop_collection[PointCloud]):
    def new(self, name: str) -> PointCloud: ...
    def remove(
        self,
        pointcloud: PointCloud,
        *,
        do_unlink: bool = True,
        do_id_user: bool = True,
        do_ui_user: bool = True,
    ) -> None: ...

###############################################################################
## Large top-level objects

class Area(bpy_struct):
    regions: bpy_prop_collection[Region]
    height: int
    width: int

    def tag_redraw(self) -> None: ...

class BlendData(bpy_struct):
    actions: BlendDataActions
    collections: BlendDataCollections
    filepath: str
    images: BlendDataImage
    materials: bpy_prop_collection[Material]
    meshes: bpy_prop_collection[Mesh]
    objects: BlendDataObjects
    particles: bpy_prop_collection[Particle]
    pointclouds: BlendDataPointClouds
    scenes: bpy_prop_collection[Scene]
    screens: bpy_prop_collection[Screen]
    texts: bpy_prop_collection[Text]
    textures: BlendDataTextures
    version: tuple[int, int, int]

class Header:
    bl_idname: str
    bl_space_type: str
    bl_region_type: str
    layout: UILayout

    def draw(self, context: Context) -> None: ...

class Menu(bpy_struct):
    bl_idname: str
    bl_label: str
    bl_description: str
    bl_owner_id: str
    layout: UILayout

    @classmethod
    def poll(cls, context: Context) -> bool: ...
    def draw(self, context: Context) -> None: ...
    def draw_preset(self, context: Context) -> None: ...

class OperatorProperties(bpy_struct): ...

class Panel(bpy_struct):
    bl_idname: str
    is_popover: bool
    layout: UILayout
    use_pin: bool

    @classmethod
    def poll(cls, context: Context) -> bool: ...
    def draw(self, context: Context) -> None: ...
    def draw_header(self, context: Context) -> None: ...
    def draw_header_preset(self, context: Context) -> None: ...

class Region(bpy_struct):
    x: int
    y: int
    width: int
    height: int

class RegionView3D(bpy_struct): ...

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

class SpaceView3D(Space):
    overlay: View3DOverlay
    shading: View3DShading

    @classmethod
    def draw_handler_add(
        cls,
        callback: Callable[..., Any],
        args: tuple[Any, ...],
        region_type: str,
        draw_type: str,
    ) -> int: ...
    @classmethod
    def draw_handler_remove(cls, handle: Any, region_type: str) -> None: ...

class Text(ID):
    name: str
    lines: bpy_prop_collection[TextLine]
    is_in_memory: bool

    @classmethod
    def from_string(cls, name: str) -> Text: ...
    def as_string(self) -> str: ...

class UIList(bpy_struct):
    bl_idname: str
    layout: UILayout
    layout_type: str
    use_filter_show: bool
    filter_name: str
    use_filter_sort_reverse: bool
    use_filter_sort_alpha: bool

    def draw_item(
        self,
        context: Context,
        layout: UILayout,
        data: bpy_struct,
        item: bpy_struct,
        icon: int,
        active_data: bpy_struct,
        active_propname: str,
        index: int = 0,
        flt_flag: int = 0,
    ) -> None: ...
    def draw_filter(self, context: Context, layout: UILayout) -> None: ...
    def filter_items(
        self, context: Context, data: bpy_struct, propname: str
    ) -> tuple[list[int], list[int]]: ...

class UILayout(bpy_struct):
    active: bool
    alert: bool
    emboss: str
    enabled: bool
    use_property_decorate: bool
    use_property_split: bool

    def box(self) -> UILayout: ...
    def column(
        self,
        *,
        align: bool = False,
        heading: str = "",
        heading_ctxt: str = "",
        translate: bool = True,
    ) -> UILayout: ...
    def label(
        self,
        *,
        text: str = "",
        text_ctct: str = "",
        translate: bool = True,
        icon: str = "NONE",
        icon_value: int = 0,
    ) -> None: ...
    def menu(
        self,
        menu: str,
        *,
        text: str = "",
        text_ctxt: str = "",
        translate: bool = True,
        icon: str = "NONE",
        icon_value: int = 0,
    ) -> None: ...
    def operator(
        self,
        operator: str,
        *,
        text: str = "",
        text_ctxt: str = "",
        translate: bool = True,
        icon: str = "NONE",
        emboss: bool = True,
        depress: bool = False,
        icon_value: int = 0,
        search_weight: float = 0.0,
        url: str = "",
    ) -> OperatorProperties: ...
    def operator_menu_enum(
        self,
        operator: str,
        property: str,
        *,
        text: str = "",
        text_ctxt: str = "",
        translate: bool = True,
        icon: str = "NONE",
    ) -> OperatorProperties: ...
    def popover(
        self,
        operator: Operator | str,
        text: str = "",
        icon: str = "NONE",
    ) -> None: ...
    def prop(
        self,
        data: bpy_struct,
        property: str,
        *,
        text: str = "",
        text_ctxt: str = "",
        translate: bool = True,
        icon: str = "NONE",
        placeholder: str = "",
        expand: bool = False,
        slider: bool = False,
        toggle: int = -1,
        icon_only: bool = False,
        event: bool = False,
        full_event: bool = False,
        emboss: bool = True,
        index: int = -1,
        icon_value: int = 0,
        invert_checkbox: bool = False,
    ) -> None: ...
    def prop_search(self, *args, **kwargs) -> None: ...
    def row(
        self,
        *,
        align: bool = False,
        heading: str = "",
        heading_ctxt: str = "",
        translate: bool = True,
    ) -> UILayout: ...
    def separator(
        self, *, factor: float = 1.0, type: Literal["AUTO", "SPACE", "LINE"] = "AUTO"
    ) -> None: ...
    def template_color_ramp(self, *args, **kwargs) -> None: ...
    def template_list(self, *args, **kwargs) -> None: ...

class View3DOverlay(bpy_struct):
    show_overlays: bool

class View3DShading(bpy_struct):
    type: Literal["WIREFRAME", "SOLID", "MATERIAL", "RENDERED"]
    color_type: Literal["MATERIAL", "OBJECT", "RANDOM", "VERTEX", "TEXTURE", "SINGLE"]
    wireframe_color_type: Literal["THEME", "OBJECT", "RANDOM"]
