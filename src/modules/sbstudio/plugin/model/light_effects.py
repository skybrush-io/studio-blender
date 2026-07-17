from __future__ import annotations

import types
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, ClassVar, Literal, Protocol, cast
from uuid import uuid4

import bpy
from bpy.path import abspath
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import (
    Collection,
    CollectionObjects,
    ColorRamp,
    Context,
    Image,
    ImageTexture,
    Mesh,
    Object,
    PropertyGroup,
    Texture,
)
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from numpy import (
    argsort,
    array,
    bool_,
    divide,
    empty,
    empty_like,
    flatnonzero,
    float32,
    isnan,
    lexsort,
    linspace,
    nan,
    rot90,
    where,
    zeros,
    zeros_like,
)
from numpy.typing import NDArray

from sbstudio.api.types import Mapping
from sbstudio.math.colors import BlendMode, blend_in_place
from sbstudio.math.rng import RandomSequence
from sbstudio.model.plane import Plane
from sbstudio.model.types import Coordinate3D, Jsonable
from sbstudio.plugin.constants import DEFAULT_LIGHT_EFFECT_DURATION, Collections
from sbstudio.plugin.meshes import use_b_mesh
from sbstudio.plugin.model.pixel_cache import PixelCache
from sbstudio.plugin.model.storyboard import StoryboardEntryOrTransition, get_storyboard
from sbstudio.plugin.presets.light_effects import (
    NULL_PRESET_ID,
    get_preset_enum_items,
    get_preset_function,
)
from sbstudio.plugin.utils import remove_if_unused, with_context
from sbstudio.plugin.utils.collections import pick_unique_name
from sbstudio.plugin.utils.color_ramp import update_color_ramp_from
from sbstudio.plugin.utils.evaluator import (
    ObjectPositions,
    get_position_of_object,
    get_positions_of_objects_fast,
)
from sbstudio.plugin.utils.image import (
    PixelsWithColorspace,
    convert_pixels_to_linear_in_place,
)
from sbstudio.plugin.utils.texture import texture_as_dict, update_texture_from_dict
from sbstudio.utils import load_module

from .mixins import ListMixin

__all__ = (
    "ColorFunctionProperties",
    "LightEffect",
    "LightEffectCollection",
    "LightEffectUpdate",
    "effect_type_supports_randomization",
    "output_type_is_experimental",
    "output_type_supports_mapping_mode",
)


CONTAINMENT_TEST_AXES = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
"""Pre-constructed vectors for a quick containment test using raycasting and BVH-trees"""

OUTPUT_TYPE_TO_AXES = {
    "GRADIENT_XYZ": (0, 1, 2),
    "GRADIENT_XZY": (0, 2, 1),
    "GRADIENT_YXZ": (1, 0, 2),
    "GRADIENT_YZX": (1, 2, 0),
    "GRADIENT_ZXY": (2, 0, 1),
    "GRADIENT_ZYX": (2, 1, 0),
    "default": (0, 0, 0),
}
"""Axis mapping for the gradient-based output types"""

OUTPUT_ITEMS = [
    ("FIRST_COLOR", "First color", "", 1),
    ("LAST_COLOR", "Last color", "", 2),
    ("INDEXED_BY_DRONES", "Indexed by drones", "", 3),
    ("INDEXED_BY_FORMATION", "Indexed by formation", "", 13),
    ("GRADIENT_XYZ", "Gradient (XYZ)", "", 4),
    ("GRADIENT_XZY", "Gradient (XZY)", "", 5),
    ("GRADIENT_YXZ", "Gradient (YXZ)", "", 6),
    ("GRADIENT_YZX", "Gradient (YZX)", "", 7),
    ("GRADIENT_ZXY", "Gradient (ZXY)", "", 8),
    ("GRADIENT_ZYX", "Gradient (ZYX)", "", 9),
    ("TEMPORAL", "Temporal", "", 10),
    ("DISTANCE", "Distance from mesh", "", 11),
    (
        "LIGHT_PRESET",
        "Light preset",
        "Built-in light effect preset (portable across machines)",
        14,
    ),
    ("CUSTOM", "Custom expression", "", 12),
]
"""Output types of light effects, determining the indexing
of drones to a given axis of the light effect color space"""


@dataclass(frozen=True)
class LightEffectUpdate:
    """Simple dataclass containing a list of drones to update and the corresponding
    colors to apply to them, in the same order.
    """

    NOP: ClassVar[LightEffectUpdate]

    drones: CollectionObjects | None
    positions: ObjectPositions | None
    colors: NDArray[float32] | None
    has_active_effects: bool

    def get_drones_and_colors(self) -> tuple[CollectionObjects, NDArray[float32]]:
        if not self.has_active_effects:
            from sbstudio.plugin.colors import get_colors_of_drones_fast

            drones = Collections.find_drones().objects
            colors: NDArray[float32] = empty((len(drones), 4), dtype=float32)
            get_colors_of_drones_fast(drones, dest=colors.ravel())

            return drones, colors
        else:
            assert self.colors is not None
            assert self.drones is not None
            return self.drones, self.colors

    def get_positions_and_colors(
        self,
    ) -> tuple[Sequence[Coordinate3D], NDArray[float32]]:
        if not self.has_active_effects:
            from sbstudio.plugin.colors import get_colors_of_drones_fast

            drones = Collections.find_drones().objects

            positions: NDArray[float32] = empty((len(drones), 4), dtype=float32)
            get_positions_of_objects_fast(drones, dest=positions.ravel())

            colors: NDArray[float32] = empty((len(drones), 4), dtype=float32)
            get_colors_of_drones_fast(drones, dest=colors.ravel())

            return positions, colors  # ty:ignore[invalid-return-type]
        else:
            assert self.positions is not None
            assert self.colors is not None
            return self.positions.as_coordinate_sequence, self.colors


LightEffectUpdate.NOP = LightEffectUpdate(None, None, None, False)


class CustomLightEffectFunction(Protocol):
    """Type of the custom light effect function, used when the output type of a light
    effect is set to "CUSTOM". The function takes the following arguments:

    - frame: the current frame index
    - time_fraction: the fraction of time passed in the current light effect relative to
      its total duration, in the [0; 1] range
    - drone_index: the index of the drone for which the output is being calculated, in
      the range [0; num_drones - 1]
    - formation_index: the index of the formation to which the drone belongs, in the
      range [0; num_formations - 1], or None if there is no formation information available
    - position: the 3D position of the drone
    - drone_count: the total number of drones in the show

    The function returns a sequence of four floats in the [0; 1] range representing the
    RGBA color on the current color ramp to apply to the drone.
    """

    def __call__(
        self,
        frame: int,
        time_fraction: float,
        drone_index: int,
        formation_index: int | None,
        position: Coordinate3D,
        drone_count: int,
    ) -> float: ...


def collection_is_drone_group(self, col: Collection) -> bool:
    drone_groups = Collections.find_drone_groups(create=False)
    return drone_groups is not None and col.name in drone_groups.children


def effect_type_supports_randomization(type: str) -> bool:
    """Returns whether the light effect type given in the argument supports
    randomization.
    """
    return type == "COLOR_RAMP" or type == "IMAGE"


def get_color_function_names(self, context: Context) -> list[tuple[str, str, str]]:
    names: list[str]

    if self.path:
        absolute_path = abspath(self.path)
        module = load_module(absolute_path)
        names = [
            name
            for name in dir(module)
            if isinstance(getattr(module, name), types.FunctionType)
        ]
    else:
        names = []

    # Always add an empty entry so we have a reasonable default for the case
    # when no module is selected
    names.insert(0, "")
    return [(name, name, "") for name in names]


def object_has_mesh_data(self, obj: Object) -> bool:
    """Filter function that accepts only those Blender objects that have a mesh
    as their associated data.
    """
    return isinstance(obj.data, Mesh)


def output_type_is_experimental(type: str) -> bool:
    """Returns whether the light effect output type given in the argument is
    experimental and may be subject to change or removal in future versions of
    the plugin."""
    return type == "LIGHT_PRESET"


def output_type_supports_mapping_mode(type: str) -> bool:
    """Returns whether the light effect output type given in the argument may
    have a mapping mode that defines how the output values are mapped to the
    [0; 1] range of the color ramp or image.
    """
    return type == "DISTANCE" or type.startswith("GRADIENT_")


def test_in_front_of(
    plane: Plane, positions: ObjectPositions, out: NDArray[bool_]
) -> None:
    """Tests whether a list of points are in front of a given plane.

    Args:
        plane: the plane to test against
        positions: the points to test
        out: an array of booleans to write the results to; must have the same length as
            ``positions``
    """
    points = positions.as_array
    plane.is_front_many(points, out=out)


def test_containment(
    bvh_tree: BVHTree, points: ObjectPositions, out: NDArray[bool_]
) -> None:
    """Given a point and a BVH-tree, tests whether a list of points are _probably_
    within the mesh represented by the BVH-tree, under the assumption that most points
    are more likely to be outside than inside.

    For each point, we cast three rays from the point in the positive X, Y and Z
    directions and check whether they intersect the mesh. If at least one of the rays
    does not intersect the mesh, we conclude that the point is outside the mesh.

    In all other cases, we assume that the point is inside the mesh. Note that this may
    lead to a small number of false positives near concave regions on the exterior of
    the mesh, close to the surface.

    Args:
        bvh_tree: the BVH-tree representing the mesh
        points: the points to test for containment
        out: an array of booleans to write the results to; must have the same length as
            ``points``
    """
    # We could do a check for the angle between the vector pointing from the point to
    # the nearest point on the mesh and the normal vector of the mesh at the nearest
    # point, but benchmarks have shown that it is actually slower than the simple
    # multi-axis test done below.
    out.fill(True)
    for index, point in enumerate(points.as_vectors):
        for axis in CONTAINMENT_TEST_AXES:
            _, _, _, dist = bvh_tree.ray_cast(point, axis)
            if dist is None or dist < 0:
                out[index] = False
                break


class ColorFunctionProperties(PropertyGroup):
    path = StringProperty(
        name="Color Function File",
        description="Path to the custom color function file",
        subtype="FILE_PATH",
    )

    name = EnumProperty(
        name="Color Function Name",
        description="Name of the custom color function",
        items=get_color_function_names,
        default=0,
    )

    def update_from(self, other) -> None:
        self.path = other.path
        if other.name:
            self.name = other.name

    def update_from_dict(self, data: dict[str, Any]) -> None:
        if path := data.get("path"):
            self.path = path
        if name := data.get("name"):
            self.name = name

    def as_dict(self) -> Jsonable:
        # TODO: reading self.name invokes error, but why?:
        # WARN (bpy.rna:1360): pyrna_enum_to_py: current value '0' matches no enum in
        # 'ColorFunctionProperties', '', 'name'
        return {
            "name": self.name,
            "path": self.path,
        }


def _get_frame_end(self: LightEffect) -> int:
    return self.frame_start + self.duration - 1


def _set_frame_end(self: LightEffect, value: int) -> None:
    # We prefer to keep the start frame the same and adjust the duration
    if value <= self.frame_start:
        self.frame_start = value
        self.duration = 1
    else:
        self.duration = value - self.frame_start + 1


def texture_updated(self: LightEffect, context):
    self.invalidate_color_image()


_pixel_cache = PixelCache()
"""Global cache for the pixels of images in image-based light effects."""


def invalidate_pixel_cache(static: bool = True, dynamic: bool = True) -> None:
    """Invalidates the cached pixel-based representations. Called when a new
    file is opened in Blender or when we move between frames or update the
    deps graph.
    """
    global _pixel_cache
    if static:
        _pixel_cache.clear()
    elif dynamic:
        _pixel_cache.clear_dynamic()


def _storyboard_entry_or_transition_selection_update(
    self: LightEffect, context: Context | None = None
):
    self.update_from_storyboard(context, reset_offset=True)


class LightEffect(PropertyGroup):
    """Blender property group representing a single, time- and possibly space-limited
    light effect in the drone show.
    """

    # If you add new properties below, make sure to update update_from()

    maybe_uuid_do_not_use = StringProperty(
        name="Identifier",
        description=(
            "Unique identifier for this storyboard entry; must not change "
            "throughout the lifetime of the entry."
        ),
        default="",
        options={"HIDDEN"},
    )

    enabled = BoolProperty(
        name="Enabled",
        description="Whether this light effect is enabled",
        default=True,
        options=set(),
    )

    type = EnumProperty(
        name="Effect Type",
        description="Type of the light effect: color ramp-based, image-based or custom function",
        items=[
            ("COLOR_RAMP", "Color ramp", "", 1),
            ("IMAGE", "Image", "", 2),
            ("FUNCTION", "Function", "", 3),
        ],
        default="COLOR_RAMP",
    )

    storyboard_entry_or_transition_selection = StringProperty(
        name="Storyboard entry/transition",
        description="The storyboard entry/transition attached to this light effect",
        update=_storyboard_entry_or_transition_selection_update,
    )

    storyboard_entry_or_transition = PointerProperty(
        name="Storyboard entry/transition",
        type=StoryboardEntryOrTransition,
        description="The internal storage for the storyboard entry/transition attached to this light effect",
    )

    frame_start: int = IntProperty(
        name="Start Frame",
        description="Frame when this light effect should start in the show",
        default=0,
        options=set(),
    )
    duration: int = IntProperty(
        name="Duration",
        description="Duration of this light effect",
        min=1,
        default=1,
        options=set(),
    )
    frame_end: int = IntProperty(
        name="End Frame",
        description="Frame when this light effect should end in the show",
        get=_get_frame_end,
        set=_set_frame_end,
        options=set(),
    )
    fade_in_duration: int = IntProperty(
        name="Fade in",
        description="Duration of the fade-in part of this light effect",
        default=0,
        options=set(),
    )
    fade_out_duration: int = IntProperty(
        name="Fade out",
        description="Duration of the fade-out part of this light effect",
        default=0,
        options=set(),
    )

    output = EnumProperty(
        name="Output X",
        description="Output function that determines the value that is passed through the color ramp or image horizontal (X) axis to obtain the color to assign to a drone",
        items=OUTPUT_ITEMS,
        default="LAST_COLOR",
    )

    output_function = PointerProperty(
        type=ColorFunctionProperties,
        name="Output X Function",
        description="Custom function for the output X",
    )

    output_y = EnumProperty(
        name="Output Y",
        description="Output function that determines the value that is passed through the image vertical (Y) axis to obtain the color to assign to a drone",
        items=OUTPUT_ITEMS,
        default="LAST_COLOR",
    )

    output_function_y = PointerProperty(
        type=ColorFunctionProperties,
        name="Output Y Function",
        description="Custom function for the output Y",
    )

    preset_id = EnumProperty(
        name="Preset",
        description="Built-in light effect preset",
        items=get_preset_enum_items,
        default=0,  # needs to be an int, cannot refer to NULL_PRESET_ID directly
        options=set(),
    )

    output_mapping_mode = EnumProperty(
        name="Mapping X",
        description="Specifies how the output value should be mapped to the [0; 1] range of the color ramp or image X axis",
        items=[("ORDERED", "Ordered", "", 1), ("PROPORTIONAL", "Proportional", "", 2)],
    )

    output_mapping_mode_y = EnumProperty(
        name="Mapping Y",
        description="Specifies how the output value should be mapped to the [0; 1] range of the image Y axis",
        items=[("ORDERED", "Ordered", "", 1), ("PROPORTIONAL", "Proportional", "", 2)],
    )

    influence: float = FloatProperty(
        name="Influence",
        description="Influence of this light effect on the final color of drones",
        default=1,
        soft_min=0,
        soft_max=1,
        min=0,
    )

    texture = PointerProperty(
        type=Texture,
        name="Texture",
        description=(
            "Texture of the light effect, used to hold the color ramp or the "
            "image that controls how the colors of the drones are determined"
        ),
        options={"HIDDEN"},
        update=texture_updated,
    )

    color_function = PointerProperty(
        type=ColorFunctionProperties,
        name="Color Function",
        description="Color function of the light effect",
    )

    mesh: Object | None = PointerProperty(
        type=Object,
        name="Mesh",
        description=(
            'Mesh related to the light effect; used when the output is set to "Distance" or to limit the '
            'light effect to the inside or one side of this mesh when "Inside the mesh" or '
            '"Front side of plane" is checked'
        ),
        poll=object_has_mesh_data,
    )

    drone_group: Collection | None = PointerProperty(
        type=Collection,
        name="Drone Group",
        description=(
            "Drone group related to the light effect; the light effect will only be "
            "targeted to the drones in this group"
        ),
        poll=collection_is_drone_group,
    )

    target = EnumProperty(
        name="Target",
        description=(
            "Specifies whether to apply this light effect to all drones or only"
            " to those drones that are inside the given mesh or are in front of"
            " the plane of the first face of the mesh or are in drone group. See also the 'Invert'"
            " property"
        ),
        items=[
            ("ALL", "All drones", "", 1),
            ("INSIDE_MESH", "Inside the mesh", "", 2),
            ("FRONT_SIDE", "Front side of plane", "", 3),
        ],
        default="ALL",
    )

    randomness = FloatProperty(
        name="Randomness",
        description=(
            "Offsets the output value of each drone randomly, wrapped around"
            "the edges of the color ramp; this property defines the maximum"
            "range of the offset"
        ),
        default=0,
        min=0,
        soft_min=0,
        soft_max=1,
        precision=2,
    )

    blend_mode = EnumProperty(
        name="Blend mode",
        description="Specifies the blending mode of this light effect",
        items=[
            (member.name, member.description, "", member.value) for member in BlendMode
        ],
        default=BlendMode.NORMAL.name,
    )

    invert_target = BoolProperty(
        name="Invert target",
        description=(
            "Invert the effect target; when checked, applies the effect to"
            " those drones that do not match the target"
        ),
        default=False,
        options=set(),
    )

    # If you add new properties above, make sure to update update_from()

    def apply_on_colors(
        self,
        colors: NDArray[float32],
        drones: Sequence[Object],
        positions: ObjectPositions,
        mapping: Mapping | None,
        *,
        frame: int,
        random_seq: RandomSequence,
    ) -> None:
        """Applies this effect to a given list of colors, each belonging to a
        given spatial position in the given frame.

        Parameters:
            colors: the colors to modify in-place
            drones: the drone objects
            positions: the spatial positions of the drones having the given
                colors in 3D space
            mapping: optional mapping of positions to match colors;
                used only by the ``INDEXED_BY_FORMATION`` output type
            frame: the frame index
            random_seq: a random sequence that is used to spread out the items
                on the color ramp or a principal axis of the image if
                randomization is turned on
        """

        # Do some quick checks to decide whether we need to bother at all
        if not self.enabled or not self.contains_frame(frame):
            return

        num_positions = len(positions)

        color_ramp = self.color_ramp
        color_image = self.color_image
        color_function_ref = self.color_function_ref

        # Calculate the influence of the effect, depending on the fade-in and fade-out
        # durations and the spatial predicate
        influence = self._evaluate_influence(frame)
        if influence <= 0:
            return

        # Allocate mask
        mask: NDArray[bool_] = zeros((num_positions,), dtype=bool_)

        # Mask all the drones that are not in the group being targeted by this effect
        # or are not matched by the spatial predicate associated to this effect
        self._mask_drones_not_in_group(mask, drones)
        self._mask_drones_not_matching_spatial_predicate(mask, positions)

        # Bail out here if no drones remained
        if mask.all():
            return

        # Determine whether we will need the X and the Y output values
        needs_output_y = color_image is not None
        needs_output_x = color_ramp is not None or color_image is not None

        # Evaluate the X and Y values for each drone
        if needs_output_x:
            outputs_x: NDArray[float32] = zeros_like(mask, dtype=float32)
            outputs_x_is_constant = self._get_output_based_on_output_type(
                frame, positions, mapping, "x", out=outputs_x
            )
            mask |= isnan(outputs_x)

        if needs_output_y:
            outputs_y: NDArray[float32] = zeros_like(outputs_x)
            self._get_output_based_on_output_type(
                frame, positions, mapping, "y", out=outputs_y
            )
            mask |= isnan(outputs_y)

        # Randomize the outputs if needed. NaNs in the output arrays are okay, they will
        # remain NaN.
        # TODO(ntamas): if possible, calculate only for the non-masked drones
        if self.randomness != 0:
            if needs_output_x:
                offsets = (
                    random_seq.get_array_01(0, num_positions) - 0.5
                ) * self.randomness
                outputs_x += offsets
                outputs_x %= 1.0
                outputs_x_is_constant = False
            if needs_output_y:
                offsets = (
                    random_seq.get_array_01(num_positions, num_positions) - 0.5
                ) * self.randomness
                outputs_y += offsets
                outputs_y %= 1.0

        unmasked = flatnonzero(~mask)

        # Apply the color ramp, image or function to get the new color. The order
        # of conditions below is according to their expected frequency of use, with
        # the most common case first.
        #
        # Note that the getters that these values come from are constructed in a
        # way that they are set to `None` if they are not applicable, so only one of
        # the branches will apply below.
        new_colors: NDArray[float32] = zeros_like(colors)
        if color_ramp is not None:
            # TODO(ntamas): if all the values in output_x are the same, there is no
            # need to evaluate it multiple times on the color ramp
            assert needs_output_x

            if outputs_x_is_constant and num_positions > 0:
                # Optimize for the common case when the output is constant
                new_colors[unmasked, :] = color_ramp.evaluate(outputs_x[0])
            else:
                for index in unmasked:
                    new_colors[index, :] = color_ramp.evaluate(outputs_x[index])

        elif color_function_ref is not None:
            time_fraction = self._get_time_fraction_for_frame(frame)
            position_seq = positions.as_coordinate_sequence
            for index in unmasked:
                try:
                    new_colors[index, :] = color_function_ref(
                        frame=frame,
                        time_fraction=time_fraction,
                        drone_index=index,
                        formation_index=(
                            mapping[index] if mapping is not None else None
                        ),
                        position=position_seq[index],
                        drone_count=num_positions,
                    )
                except Exception as exc:
                    raise RuntimeError("ERROR_COLOR_FUNCTION") from exc

        elif color_image is not None:
            assert needs_output_x and needs_output_y

            width, height = color_image.size
            pixels_with_colorspace = self.get_image_pixels()

            if pixels_with_colorspace is None:
                new_colors.fill(0.0)
            else:
                xs = (width * outputs_x[unmasked]).astype(int)
                ys = (height * outputs_y[unmasked]).astype(int)
                xs = where(xs < width, xs, width - 1)
                ys = where(ys < height, ys, height - 1)

                chosen_pixels: NDArray[float32] = pixels_with_colorspace.pixels[ys, xs]
                convert_pixels_to_linear_in_place(
                    chosen_pixels, pixels_with_colorspace.colorspace
                )

                new_colors[unmasked, :] = chosen_pixels

        else:
            # should not happen
            new_colors.fill(1.0)

        # Scale the alpha channel of the new colors with the influence
        new_colors[:, 3] *= where(mask, 0, influence)

        # Apply the new color with alpha blending
        blend_in_place(new_colors, colors, BlendMode[self.blend_mode])

    def as_dict(self) -> Jsonable:
        """Creates a dictionary representation of the light effect."""
        # Hint: synchronize content of this function with self.update_from()
        return {
            "enabled": self.enabled,
            "frameStart": self.frame_start,
            "duration": self.duration,
            "fadeInDuration": self.fade_in_duration,
            "fadeOutDuration": self.fade_out_duration,
            "output": self.output,
            "outputY": self.output_y,
            "influence": self.influence,
            "meshName": self.mesh.name if self.mesh else None,
            "droneGroupName": self.drone_group.name if self.drone_group else None,
            "target": self.target,
            "randomness": self.randomness,
            "outputMappingMode": self.output_mapping_mode,
            "outputMappingModeY": self.output_mapping_mode_y,
            "blendMode": self.blend_mode,
            "type": self.type,
            "invertTarget": self.invert_target,
            "colorFunction": self.color_function.as_dict(),
            "presetId": self.preset_id,
            "outputFunction": self.output_function.as_dict(),
            "outputFunctionY": self.output_function_y.as_dict(),
            "storyboardEntryOrTransition": self.storyboard_entry_or_transition_selection,
            "texture": texture_as_dict(self.texture),
        }

    @property
    def color_ramp(self) -> ColorRamp | None:
        """The color ramp of the effect, if it exists and is being used according
        to the type of the effect.
        """
        return self.texture.color_ramp if self.type == "COLOR_RAMP" else None

    @property
    def color_image(self) -> Image | None:
        """The color image of the effect, if it exists and is being used according
        to the type of the effect.
        """
        return (
            self.texture.image
            if self.type == "IMAGE" and isinstance(self.texture, ImageTexture)
            else None
        )

    @color_image.setter
    def color_image(self, image: Image | None):
        # If we have an old, legacy Texture instance, replace it with an
        # ImageTexture
        if isinstance(self.texture, ImageTexture):
            tex = self.texture
        else:
            self._remove_texture()
            tex = self._create_texture()

        if tex.image is not None:
            remove_if_unused(tex.image, from_=bpy.data.images)
        tex.image = image

        self.invalidate_color_image()

    @property
    def color_function_ref(self) -> Callable | None:
        """The color function used to calculate the effect, if it exists and is being
        used according to the type of the effect.
        """
        if self.type != "FUNCTION" or not self.color_function:
            return None

        absolute_path = abspath(self.color_function.path)
        module = load_module(absolute_path)
        return getattr(module, self.color_function.name, None)

    def contains_frame(self, frame: int) -> bool:
        """Returns whether the light effect contains the given frame.

        Light effect entries are closed from the left and right as well to
        remain consistent with how Blender is handling frame intervals.
        in other words, they always contain their start frames and end frames.
        """
        return 0 <= (frame - self.frame_start) < self.duration

    def create_color_image(
        self, name: str, width: int, height: int, *, color_space: str = "Linear Rec.709"
    ) -> Image:
        """Creates a new color image for the light effect with the given color space
        (and deletes the old one if it already has one).

        Args:
            name: the name of the image to create
            width: the width of the image in pixels, corresponding to the
                time axis of the color animation
            height: the height of the image in pixels, corresponding to
                the number of drones to color
            color_space: the color space to set on the image

        Returns:
            the created color image itself for easy chaining
        """
        image = bpy.data.images.new(name=name, width=width, height=height)
        image.colorspace_settings.name = color_space
        self.color_image = image
        return image

    @property
    def duration_offset(self) -> int:
        """Returns the duration offset relative to attached storyboard entry duration,
        or zero if no storyboard entry is attached."""
        return self.frame_end_offset - self.frame_start_offset

    @property
    def frame_end_offset(self) -> int:
        """Returns frame offset relative to attached storyboard entry end,
        or zero if no storyboard entry is attached."""
        if self.storyboard_entry_or_transition_selection:
            return self.frame_end - self.storyboard_entry_or_transition.frame_end
        else:
            return 0

    @property
    def frame_start_offset(self) -> int:
        """ "Returns the frame offset relative to attached storyboard entry start,
        or zero if no storyboard entry is attached."""
        if self.storyboard_entry_or_transition_selection:
            return self.frame_start - self.storyboard_entry_or_transition.frame_start
        else:
            return 0

    def get_image_pixels(self) -> PixelsWithColorspace | None:
        """Returns the pixel-level representation of the color image of the light
        effect, caching the result for future use.
        """
        global _pixel_cache
        pixels = _pixel_cache.get(self.id)
        if pixels is None and self.color_image is not None:
            pixels = _pixel_cache.add_image(
                self.id, self.color_image, is_static=not self.is_animated
            )

        return pixels

    @property
    def id(self) -> str:
        """Unique identifier of this light effect."""
        if not self.maybe_uuid_do_not_use:
            # Chance of a collision is minimal so just use random numbers
            self.maybe_uuid_do_not_use = uuid4().hex
        return self.maybe_uuid_do_not_use

    @property
    def is_animated(self) -> bool:
        """Returns whether this light effect is animated, i.e. whether it has
        an associated image texture that has more than one frame.
        """
        return self.color_image is not None and self.color_image.frame_duration > 1

    def invalidate_color_image(self) -> None:
        """Invalidates the cached pixel-level representation of the color image
        of the light effect.

        You should call this function if you change the _pixel buffer_ of the
        underlying image. You do not need to call this function if you replace
        the image by calling the setter of `color_image`.
        """
        global _pixel_cache
        try:
            _pixel_cache.remove(self.id)
        except KeyError:
            pass  # this is OK

    def update_from(self, other: "LightEffect") -> None:
        """Updates the properties of this light effect from another one,
        _except_ its name.
        """
        # UUID not copied, this is intentional
        self.enabled = other.enabled
        self.frame_start = other.frame_start
        self.duration = other.duration
        self.fade_in_duration = other.fade_in_duration
        self.fade_out_duration = other.fade_out_duration
        self.output = other.output
        self.output_y = other.output_y
        self.influence = other.influence
        self.mesh = other.mesh
        self.drone_group = other.drone_group
        self.target = other.target
        self.randomness = other.randomness
        self.output_mapping_mode = other.output_mapping_mode
        self.output_mapping_mode_y = other.output_mapping_mode_y
        self.blend_mode = other.blend_mode
        self.type = other.type
        self.color_image = other.color_image
        self.invert_target = other.invert_target

        try:
            self.preset_id = other.preset_id
        except TypeError:
            # This happens if other.preset_id is empty or some other unsupported value
            # that is not present in the enum spec any more
            self.preset_id = NULL_PRESET_ID

        self.color_function.update_from(other.color_function)
        self.output_function.update_from(other.output_function)
        self.output_function_y.update_from(other.output_function_y)

        self.storyboard_entry_or_transition_selection = (
            other.storyboard_entry_or_transition_selection
        )

        if self.color_ramp is not None:
            assert other.color_ramp is not None  # because we copied the type
            update_color_ramp_from(self.color_ramp, other.color_ramp)

    def update_from_dict(self, data: dict[str, Any]) -> list[str]:
        """Updates the properties of this light effect from its dictionary representation.

        Returns:
            a list of warnings generated while updating the light effect
        """
        warnings: list[str] = []

        # Note that we do _not_ load UUID and name, this is intentional
        # Hint: synchronize content of this function with self.update_from()
        if enabled := data.get("enabled"):
            self.enabled = enabled
        if frame_start := data.get("frameStart"):
            self.frame_start = frame_start
        if duration := data.get("duration"):
            self.duration = duration
        if fade_in_duration := data.get("fadeInDuration"):
            self.fade_in_duration = fade_in_duration
        if fade_out_duration := data.get("fadeOutDuration"):
            self.fade_out_duration = fade_out_duration
        if output := data.get("output"):
            self.output = output
        if output_y := data.get("outputY"):
            self.output_y = output_y
        if influence := data.get("influence"):
            self.influence = influence
        if mesh_name := data.get("meshName"):
            if mesh_name in bpy.data.objects:
                self.mesh = bpy.data.objects[mesh_name]
            else:
                warnings.append(
                    f"Could not import mesh: object {mesh_name!r} is not part of the current file"
                )
        if drone_group_name := data.get("droneGroupName"):
            if drone_group_name in bpy.data.collections:
                self.drone_group = bpy.data.collections[drone_group_name]
            else:
                warnings.append(
                    f"Could not import drone group: collection {drone_group_name!r} is not part of the current file"
                )
        if target := data.get("target"):
            self.target = target
        if randomness := data.get("randomness"):
            self.randomness = randomness
        if output_mapping_mode := data.get("outputMappingMode"):
            self.output_mapping_mode = output_mapping_mode
        if output_mapping_mode_y := data.get("outputMappingModeY"):
            self.output_mapping_mode_y = output_mapping_mode_y
        if blend_mode := data.get("blendMode"):
            self.blend_mode = blend_mode
        if effect_type := data.get("type"):
            self.type = effect_type
        if invert_target := data.get("invertTarget"):
            self.invert_target = invert_target

        if color_function := data.get("colorFunction"):
            self.color_function.update_from_dict(color_function)
        if output_function := data.get("outputFunction"):
            self.output_function.update_from_dict(output_function)
        if output_function_y := data.get("outputFunctionY"):
            self.output_function_y.update_from_dict(output_function_y)

        if storyboard_entry_or_transition_selection := data.get(
            "storyboardEntryOrTransition"
        ):
            self.storyboard_entry_or_transition_selection = (
                storyboard_entry_or_transition_selection
            )

        if texture := data.get("texture"):
            assert isinstance(self.texture, ImageTexture)
            warnings.extend(update_texture_from_dict(self.texture, texture))

        return warnings

    def update_from_storyboard(
        self, context: Context | None, *, reset_offset: bool
    ) -> None:
        """Updates the stored storyboard entry/transition's name and
        start and end times from the currently selected entry/transition."""

        # save current offsets
        start_offset = 0 if reset_offset else self.frame_start_offset
        end_offset = 0 if reset_offset else self.frame_end_offset

        # update our own storyboard entry pointer from the name
        # property that is updated by the prop search dropdown
        storyboard = get_storyboard(context=context)
        entry = storyboard.get_entry_or_transition_by_name(
            self.storyboard_entry_or_transition_selection
        )
        if entry is not None:
            # update start and end times with previous offsets and
            # possibly new storyboard start/end times
            self.storyboard_entry_or_transition.update_from(entry)
            self.frame_start = (
                self.storyboard_entry_or_transition.frame_start + start_offset
            )
            self.frame_end = self.storyboard_entry_or_transition.frame_end + end_offset

    def _create_texture(self) -> ImageTexture:
        """Creates the texture associated to the light effect."""
        tex = bpy.data.textures.new(
            name=f"Texture for light effect {self.name!r}", type="IMAGE"
        )
        tex.use_color_ramp = True
        tex.image = None

        # Clear alpha from color ramp
        elts = tex.color_ramp.elements
        for elt in elts:
            elt.color[3] = 1.0

        self.texture = tex
        return self.texture

    def _remove_texture(self) -> None:
        """Removes the texture associated to the light effect from the Textures
        collection if there are no other users for the texture in the scene.
        """
        if isinstance(self.texture, ImageTexture):
            if self.texture.image is not None:
                remove_if_unused(self.texture.image, from_=bpy.data.images)

        remove_if_unused(self.texture, from_=bpy.data.textures)

    ####################################################################################
    ## Helper functions for effect evaluation only
    ####################################################################################

    def _evaluate_influence(self, frame: int) -> float:
        """Returns the common influence value of this effect, modifying it in the
        fade-in and fade-out periods as needed.

        The returned value is guaranteed to be in [0; 1].
        """
        influence = self.influence

        # Apply fade-in
        if self.fade_in_duration > 0:
            diff = frame - self.frame_start + 1
            if diff < self.fade_in_duration:
                influence *= diff / self.fade_in_duration

        # Apply fade_out
        if self.fade_out_duration > 0:
            diff = self.frame_end - frame
            if diff < self.fade_out_duration:
                influence *= diff / self.fade_out_duration

        return min(max(influence, 0), 1)

    def _get_bvh_tree_from_mesh(self) -> BVHTree | None:
        """Returns a BVH-tree data structure from the mesh associated to this
        light effect for easy containment detection, or `None` if the light
        effect has no associated mesh.
        """
        if self.mesh and self.mesh.data:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            mesh = self.mesh

            obj = depsgraph.objects.get(mesh.name)
            if obj and obj.data:
                # Object is in the evaluated depsgraph so we use the mesh data
                # from there
                ev_mesh = cast(Mesh, obj.data)
                ev_mesh.transform(mesh.matrix_world)
                tree = BVHTree.FromObject(obj, depsgraph, deform=True)
                ev_mesh.transform(mesh.matrix_world.inverted())
            else:
                # Object is not in the evaluated depsgraph -- maybe it is
                # hidden? Use self.mesh directly
                mesh_data = cast(Mesh, mesh.data)
                with use_b_mesh() as b_mesh:
                    # We don't request the normals here because we need to update them
                    # anyway after calling transform(). normal_update() is mandatory,
                    # otherwise there are slight issues with the containment test such
                    # that it does not give the same result when the mesh is hidden
                    # (not in the deps graph).
                    b_mesh.from_mesh(
                        mesh_data, vertex_normals=False, face_normals=False
                    )
                    b_mesh.transform(mesh.matrix_world)
                    b_mesh.normal_update()
                    tree = BVHTree.FromBMesh(b_mesh)
            return tree

    def _get_plane_from_mesh(self) -> Plane | None:
        """Returns a plane that is an infinite expansion of the first face of the
        mesh associated to this light effect, or `None` if the light effect has
        no associated mesh or it has no faces.
        """
        if self.mesh:
            mesh = cast(Mesh, self.mesh.data)
            local_to_world = self.mesh.matrix_world
            for polygon in mesh.polygons:
                normal = local_to_world.to_3x3() @ polygon.normal
                center = local_to_world @ polygon.center
                try:
                    return Plane.from_normal_and_point(normal, center)
                except Exception:
                    # probably all-zero normal vector
                    pass

    def _get_time_fraction_for_frame(self, frame: int) -> float:
        return (frame - self.frame_start) / max(self.duration - 1, 1)

    def _get_spatial_effect_predicate(
        self,
    ) -> Callable[[ObjectPositions, NDArray[bool_]], None] | None:
        match self.target:
            case "INSIDE_MESH":
                bvh_tree = self._get_bvh_tree_from_mesh()
                return (
                    partial(test_containment, bvh_tree)
                    if bvh_tree is not None
                    else None
                )

            case "FRONT_SIDE":
                plane = self._get_plane_from_mesh()
                return partial(test_in_front_of, plane) if plane is not None else None

    def _get_output_based_on_output_type(
        self,
        frame: int,
        positions: ObjectPositions,
        mapping: Mapping | None,
        axis: Literal["x", "y"],
        *,
        out: NDArray[float32],
    ) -> bool:
        """Get the float outputs for color ramp or image indexing based on the
        output type.

        Args:
            out: destination array to write the result to

        Returns:
            whether the output is constant
        """
        output_type = self.output_y if axis == "y" else self.output
        num_positions = len(positions)

        if output_type == "FIRST_COLOR":
            out.fill(0.0)
            return True

        elif output_type == "LAST_COLOR":
            out.fill(1.0)
            return True

        elif output_type == "TEMPORAL":
            time_fraction = self._get_time_fraction_for_frame(frame)
            out.fill(time_fraction)
            return True

        elif output_type_supports_mapping_mode(output_type):
            # There are two options here:
            #
            # 1. Legacy, non-proportional mode. We sort the drones based on a
            #    sort key and then space them out equally on the color ramp or
            #    image axis.
            #
            # 2. Proportional mode. Same as above, but we assign drones to
            #    positions on the color ramp or image axis in a way that their
            #    distances on the color ramp or image axis are proportional to
            #    the differences in their sort keys. Note that this needs a
            #    _scalar_ sorting key so we ignore all but the principal axis
            #    for gradient output types.
            mapping_mode = (
                self.output_mapping_mode_y if axis == "y" else self.output_mapping_mode
            )
            proportional = mapping_mode == "PROPORTIONAL"
            sort_keys: NDArray[float32] | None

            if output_type == "DISTANCE":
                if self.mesh:
                    position_of_mesh = array(
                        get_position_of_object(self.mesh), dtype=float32
                    )
                    sort_keys = ((positions - position_of_mesh) ** 2).sum(axis=1)
                else:
                    sort_keys = None

            else:
                query_axes = (
                    OUTPUT_TYPE_TO_AXES.get(output_type)
                    or OUTPUT_TYPE_TO_AXES["default"]
                )
                if proportional:
                    # In proportional mode, we are using the primary axis only
                    # because we need a scalar
                    sort_keys = positions.as_array[:, query_axes[0]]
                else:
                    # In non-proportional mode, we are sorting along multiple axes
                    sort_keys = positions.as_array[:, query_axes]

            if num_positions < 2 or sort_keys is None:
                # Just assign all drones to the last color of the ramp
                out.fill(1.0)
            elif proportional:
                # In proportional mode, sort_keys is always 1D and we need to just
                # re-scale the values to the 0-1 range
                assert sort_keys.ndim == 1
                if len(sort_keys) > 0:
                    lo, hi = sort_keys.min(), sort_keys.max()
                    if hi > lo:
                        sort_keys -= lo
                        divide(sort_keys, hi - lo, out=out)
            else:
                # In legacy mode, sort_keys is either 1D or 2D
                if sort_keys.ndim == 2:
                    # 2D case, we need to do a lexicographic sort
                    order = lexsort(rot90(sort_keys))
                else:
                    assert sort_keys.ndim == 1
                    order = argsort(sort_keys)

                out[:] = argsort(order)
                out /= num_positions - 1

        elif output_type == "INDEXED_BY_DRONES":
            # Gradient based on drone index
            if num_positions > 1:
                out[:] = linspace(0.0, 1.0, num=num_positions)
            else:
                out.fill(1.0)

        elif output_type == "INDEXED_BY_FORMATION":
            # Gradient based on formation index
            if mapping is not None:
                assert num_positions == len(mapping)

                # TODO: this now works only if the number of valid entries in the mapping
                # is consistent with the number of drones in the given formation;
                # e.g., it will not work with two formations of half size at the same time
                # for this case, single-formation specific mapping would be needed

                # reduce mapping of all positions to rank, in case formation size
                # is smaller than the number of drones
                # TODO(ntamas): this would probably be faster with NumPy
                if None in mapping:
                    sorted_valid_mapping = sorted(x for x in mapping if x is not None)
                    np_m1 = max(len(sorted_valid_mapping) - 1, 1)
                    out[:] = [
                        nan if x is None else sorted_valid_mapping.index(x) / np_m1
                        for x in mapping
                    ]
                # otherwise just normalize full mapping to [0, 1]
                else:
                    np_m1 = max(num_positions - 1, 1)
                    divide(cast(Sequence[int], mapping), np_m1, out=out)
            else:
                # if there is no mapping at all, we do not change color of drones
                out.fill(nan)

        elif output_type == "CUSTOM":
            position_seq = positions.as_coordinate_sequence
            output_function = (
                self.output_function_y if axis == "y" else self.output_function
            )
            absolute_path = abspath(output_function.path)
            module = load_module(absolute_path) if absolute_path else None
            if output_function.name:
                fn = cast(
                    CustomLightEffectFunction, getattr(module, output_function.name)
                )
                time_fraction = self._get_time_fraction_for_frame(frame)
                out[:] = [
                    fn(
                        frame=frame,
                        time_fraction=time_fraction,
                        drone_index=index,
                        formation_index=(
                            mapping[index] if mapping is not None else None
                        ),
                        position=position_seq[index],
                        drone_count=num_positions,
                    )
                    for index in range(num_positions)
                ]
            else:
                out.fill(1.0)
                return True

            # TODO(ntamas): add CUSTOM_VECTORIZED type

        elif output_type == "LIGHT_PRESET":
            position_seq = positions.as_coordinate_sequence
            preset_fn = get_preset_function(self.preset_id) if self.preset_id else None
            if preset_fn is not None:
                time_fraction = self._get_time_fraction_for_frame(frame)
                out[:] = [
                    preset_fn(
                        frame=frame,
                        time_fraction=time_fraction,
                        drone_index=index,
                        formation_index=(
                            mapping[index] if mapping is not None else None
                        ),
                        position=position_seq[index],
                        drone_count=num_positions,
                    )
                    for index in range(num_positions)
                ]
            else:
                out.fill(1.0)
                return True

        else:
            # Should not get here
            out.fill(1.0)
            return True

        return False

    def _mask_drones_not_in_group(
        self, mask: NDArray[bool_], all_drones: Sequence[Object]
    ) -> None:
        """Masks all drones that are not in the drone group associated with this effect.
        No-op if the effect has no associated group.
        """
        if self.drone_group is None:
            return

        drones_in_group = set(self.drone_group.objects)
        for index, drone in enumerate(all_drones):
            if drone in drones_in_group:
                mask[index] = True

    def _mask_drones_not_matching_spatial_predicate(
        self, mask: NDArray[bool_], positions: ObjectPositions
    ) -> None:
        """Masks all drones that do not match the spatial predicate associated with this
        effect. No-op if the effect has no spatial predicate.
        """
        predicate: Callable[[ObjectPositions, NDArray[bool_]], None] | None = (
            self._get_spatial_effect_predicate()
        )
        if not predicate:
            if self.invert_target:
                mask.fill(True)
            return

        # TODO(ntamas): re-write predicates so they update the mask and do not
        # even bother testing those drones that are already excluded at this point
        result = empty_like(mask)
        predicate(positions, result)
        mask |= result if self.invert_target else ~result


class LightEffectCollection(PropertyGroup, ListMixin[LightEffect]):
    """Blender property group representing the list of light effects to apply
    on the drones in the drone show.
    """

    enabled = BoolProperty(
        name="Light Effects",
        description="Enable or disable all light effects globally. Disabling them should increase framerate significantly",
        default=True,
        options=set(),
    )
    """Global toggle for all light effects."""

    entries = CollectionProperty(type=LightEffect)
    """The entries in the collection."""

    active_entry_index: int = IntProperty(
        name="Selected index",
        description="Index of the light effect currently being edited",
    )
    """Index of the active entry (currently being edited)."""

    @property
    def active_entry(self) -> LightEffect | None:
        """The active light effect entry currently selected for editing, or
        `None` if there is no such entry.
        """
        index = self.active_entry_index
        if index is not None and index >= 0 and index < len(self.entries):
            return self.entries[index]
        else:
            return None

    @with_context
    def append_new_entry(
        self,
        name: str,
        frame_start: int | None = None,
        duration: int | None = None,
        *,
        select: bool = False,
        context: Context | None = None,
    ) -> LightEffect:
        """Appends a new light effect to the end of the light effect list.

        Parameters:
            name: the name of the new entry
            frame_start: the start frame of the new entry; `None` chooses a
                sensible default
            duration: the duration of the new entry in frames; `None` chooses a
                sensible default
            select: whether to select the newly added entry after it was created
        """
        assert context is not None

        scene = context.scene

        fps = scene.render.fps
        if frame_start is None:
            # TODO(ntamas): choose the start of the formation that includes the
            # current frame or transition
            frame_start = scene.frame_start

        if duration is None or duration <= 0:
            duration = fps * DEFAULT_LIGHT_EFFECT_DURATION

        entry = self.entries.add()
        entry.type = "COLOR_RAMP"
        entry.frame_start = frame_start
        entry.duration = duration
        # TODO(ntamas,vasarhelyi): propose unique name
        entry.name = name

        texture = entry._create_texture()

        # Copy default colors from the LED Control panel
        if hasattr(scene, "skybrush") and hasattr(scene.skybrush, "led_control"):
            led_control = scene.skybrush.led_control
            elts = texture.color_ramp.elements
            last_elt = len(elts) - 1
            for i in range(3):
                elts[0].color[i] = led_control.primary_color[i]
                if last_elt > 0:
                    elts[last_elt].color[i] = led_control.secondary_color[i]

        if select:
            self.active_entry_index = len(self.entries) - 1

        return entry

    @with_context
    def duplicate_selected_entry(
        self,
        *,
        select: bool = False,
        context: Context | None = None,
    ) -> LightEffect:
        """Duplicates the selected entry in the light effect list.

        Parameters:
            name: the name of the new entry
            frame_start: the start frame of the new entry; `None` chooses a
                sensible default
            duration: the duration of the new entry; `None` chooses a sensible
                default
            select: whether to select the newly added entry after it was created

        Returns:
            the duplicate of the selected entry
        """
        active_entry = self.active_entry
        if not active_entry:
            raise RuntimeError("no selected entry in light effect list")

        index = self.active_entry_index
        assert index is not None

        entry = self.append_new_entry(
            name=pick_unique_name(active_entry.name, self.entries)
        )

        # For some reason this invalidates `active_entry` or at least the
        # texture on it, at least in Blender 4.x, so it is best to query the
        # entry again. Blender is weird.
        entry_to_duplicate = self.entries[index]

        entry.update_from(entry_to_duplicate)
        self.entries.move(len(self.entries) - 1, index + 1)

        if select:
            self.active_entry_index = index + 1

        return entry

    @property
    def frame_end(self) -> int:
        """Returns the index of the last (open ended) frame of the light effects."""
        return (
            max(entry.frame_end for entry in self.entries)
            if self.entries
            else self.frame_start
        )

    @property
    def frame_start(self) -> int:
        """Returns the index of the first frame that is covered by light effects."""
        return (
            min(entry.frame_start for entry in self.entries)
            if self.entries
            else bpy.context.scene.frame_start
        )

    def get_index_of_entry_containing_frame(self, frame: int) -> int:
        """Returns the index of an arbitrary light effect containing the given
        frame.

        Returns:
            the index of an arbitrary light effect containing the given frame, or
            -1 if the current frame does not belong to any of the entries
        """
        for index, entry in enumerate(self.entries):
            if entry.contains_frame(frame):
                return index
        return -1

    def iter_active_effects_in_frame(self, frame: int) -> Iterable[LightEffect]:
        """Iterates over all effects that are active in the given frame."""
        # TODO(ntamas): use an interval tree if this becomes a performance
        # bottleneck
        if not self.enabled:
            return
        for entry in self.entries:
            if entry.enabled and entry.influence > 0 and entry.contains_frame(frame):
                yield entry

    def update_from_storyboard(self, context: Context) -> None:
        for entry in self.entries:
            entry.update_from_storyboard(context, reset_offset=False)

    def _on_removing_entry(self, entry) -> bool:
        entry._remove_texture()
        return True
