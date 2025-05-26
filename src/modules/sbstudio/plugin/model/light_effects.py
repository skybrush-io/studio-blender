from __future__ import annotations

import types
import bpy

from collections.abc import Callable, Iterable, Sequence
from functools import partial
from operator import itemgetter
from typing import cast, Optional
from uuid import uuid4

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
    ColorRamp,
    Context,
    Image,
    ImageTexture,
    PropertyGroup,
    Mesh,
    Object,
    Texture,
)
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from sbstudio.math.colors import blend_in_place, BlendMode
from sbstudio.math.rng import RandomSequence
from sbstudio.model.plane import Plane
from sbstudio.model.types import Coordinate3D, MutableRGBAColor
from sbstudio.plugin.constants import DEFAULT_LIGHT_EFFECT_DURATION
from sbstudio.plugin.meshes import use_b_mesh
from sbstudio.plugin.model.pixel_cache import PixelCache
from sbstudio.plugin.utils import remove_if_unused, with_context
from sbstudio.plugin.utils.collections import pick_unique_name
from sbstudio.plugin.utils.color_ramp import update_color_ramp_from
from sbstudio.plugin.utils.evaluator import get_position_of_object
from sbstudio.plugin.utils.image import convert_from_srgb_to_linear
from sbstudio.utils import constant, distance_sq_of, load_module, negate

from .mixins import ListMixin


__all__ = ("ColorFunctionProperties", "LightEffect", "LightEffectCollection")


def object_has_mesh_data(self, obj) -> bool:
    """Filter function that accepts only those Blender objects that have a mesh
    as their associated data.
    """
    return obj.data and isinstance(obj.data, Mesh)


CONTAINMENT_TEST_AXES = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
"""Pre-constructed vectors for a quick containment test using raycasting and BVH-trees"""

OUTPUT_TYPE_TO_AXIS_SORT_KEY = {
    "GRADIENT_XYZ": (0, 1, 2),
    "GRADIENT_XZY": (0, 2, 1),
    "GRADIENT_YXZ": (1, 0, 2),
    "GRADIENT_YZX": (1, 2, 0),
    "GRADIENT_ZXY": (2, 0, 1),
    "GRADIENT_ZYX": (2, 1, 0),
    "default": (0, 0, 0),
}
"""Axis mapping for the gradient-based output types"""

OUTPUT_TYPE_TO_AXIS_SORT_KEY = {
    key: itemgetter(*value) for key, value in OUTPUT_TYPE_TO_AXIS_SORT_KEY.items()
}

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
    ("CUSTOM", "Custom expression", "", 12),
]
"""Output types of light effects, determining the indexing
of drones to a given axis of the light effect color space"""


def effect_type_supports_randomization(type: str) -> bool:
    """Returns whether the light effect type given in the argument supports
    randomization.
    """
    return type == "COLOR_RAMP" or type == "IMAGE"


def output_type_supports_mapping_mode(type: str) -> bool:
    """Returns whether the light effect output type given in the argument may
    have a mapping mode that defines how the output values are mapped to the
    [0; 1] range of the color ramp or image.
    """
    return type == "DISTANCE" or type.startswith("GRADIENT_")


def test_containment(bvh_tree: Optional[BVHTree], point: Coordinate3D) -> bool:
    """Given a point and a BVH-tree, tests whether the point is _probably_
    within the mesh represented by the BVH-tree.

    This is done by casting three rays in the X, Y and Z directions. The point
    is assumed to be within the mesh if all three rays hit the mesh.

    Returns True if the BVH-tree is missing.
    """
    global CONTAINMENT_TEST_AXES

    if not bvh_tree:
        return True

    for axis in CONTAINMENT_TEST_AXES:
        _, _, _, dist = bvh_tree.ray_cast(point, axis)
        if dist is None or dist == -1:
            return False

    return True


def test_is_in_front_of(plane: Optional[Plane], point: Coordinate3D) -> bool:
    """Given a point and a plane, tests whether the point is on the front side
    of the plane.

    Returns:
        True if the point is on the front side of the plane or if the plane is
        ``None``
    """
    if plane:
        return plane.is_front(point)
    else:
        return True


_always_true = constant(True)


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

    def update_from(self, other):
        self.path = other.path
        if other.name:
            self.name = other.name


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
    file is opened in Blender.
    """
    global _pixel_cache
    if static:
        _pixel_cache.clear()
    elif dynamic:
        _pixel_cache.clear_dynamic()


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

    frame_start = IntProperty(
        name="Start Frame",
        description="Frame when this light effect should start in the show",
        default=0,
        options=set(),
    )
    duration = IntProperty(
        name="Duration",
        description="Duration of this light effect",
        min=1,
        default=1,
        options=set(),
    )
    frame_end = IntProperty(
        name="End Frame",
        description="Frame when this light effect should end in the show",
        get=_get_frame_end,
        set=_set_frame_end,
        options=set(),
    )
    fade_in_duration = IntProperty(
        name="Fade in",
        description="Duration of the fade-in part of this light effect",
        default=0,
        options=set(),
    )
    fade_out_duration = IntProperty(
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

    influence = FloatProperty(
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

    mesh = PointerProperty(
        type=Object,
        name="Mesh",
        description=(
            'Mesh related to the light effect; used when the output is set to "Distance" or to limit the '
            'light effect to the inside or one side of this mesh when "Inside the mesh" or '
            '"Front side of plane" is checked'
        ),
        poll=object_has_mesh_data,
    )

    target = EnumProperty(
        name="Target",
        description=(
            "Specifies whether to apply this light effect to all drones or only"
            " to those drones that are inside the given mesh or are in front of"
            " the plane of the first face of the mesh. See also the 'Invert'"
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
        colors: Sequence[MutableRGBAColor],
        positions: Sequence[Coordinate3D],
        mapping: Optional[list[int]],
        *,
        frame: int,
        random_seq: RandomSequence,
    ) -> None:
        """Applies this effect to a given list of colors, each belonging to a
        given spatial position in the given frame.

        Parameters:
            colors: the colors to modify in-place
            positions: the spatial positions of the drones having the given
                colors in 3D space
            mapping: optional mapping of positions to match colors;
                used only by the ``INDEXED_BY_FORMATION`` output type
            frame: the frame index
            random_seq: a random sequence that is used to spread out the items
                on the color ramp or a principal axis of the image if
                randomization is turned on
        """

        def get_output_based_on_output_type(
            output_type: str,
            mapping_mode: str,
            output_function,
        ) -> tuple[Optional[list[Optional[float]]], Optional[float]]:
            """Get the float output(s) for color ramp or image indexing based on the output type.

            Args:
                output_type: the output type used for indexing
                mapping_mode: mapping mode corresponding to the output type

            Returns:
                individual and common outputs
            """
            outputs: Optional[list[Optional[float]]] = None
            common_output: Optional[float] = None
            order: Optional[list[int]] = None

            if output_type == "FIRST_COLOR":
                common_output = 0.0
            elif output_type == "LAST_COLOR":
                common_output = 1.0
            elif output_type == "TEMPORAL":
                common_output = time_fraction
            elif output_type_supports_mapping_mode(output_type):
                # There are two options here:
                # 1. Legacy, non-proportional mode. We sort the drones based on the
                #    sort key derived above and then space them out equally on the
                #    color ramp or image axis.
                # 2. Proportional mode. Same as above, but we assign drones to
                #    positions on the color ramp or image axis in a way that their
                #    distances on the color ramp or image axis are proportional to
                #    the differences in their sort keys. Note that this needs a
                #    _scalar_ sorting key so we ignore all but the principal axis
                #    for gradient output types.
                proportional = mapping_mode == "PROPORTIONAL"

                if output_type == "DISTANCE":
                    if self.mesh:
                        position_of_mesh = get_position_of_object(self.mesh)
                        sort_key = lambda index: distance_sq_of(
                            positions[index], position_of_mesh
                        )
                    else:
                        sort_key = None

                    # sort_key is guaranteed to return a scalar here
                else:
                    query_axes = (
                        OUTPUT_TYPE_TO_AXIS_SORT_KEY.get(output_type)
                        or OUTPUT_TYPE_TO_AXIS_SORT_KEY["default"]
                    )
                    if proportional:
                        # In proportional mode, we are using the primary axis only
                        # because we need a scalar
                        sort_key = lambda index: query_axes(positions[index])[0]
                    else:
                        # In non-proportional mode, we are sorting along multiple
                        # axes
                        sort_key = lambda index: query_axes(positions[index])

                outputs = [1.0] * num_positions  # type: ignore
                order = list(range(num_positions))
                if num_positions > 1:
                    if proportional and sort_key is not None:
                        # Proportional mode -- calculate the sort key for each item,
                        # and distribute them along the color axis proportionally
                        # to the differences between the numeric values of the sort
                        # keys
                        evaluated_sort_keys = [sort_key(i) for i in order]
                        min_value, max_value = (
                            min(evaluated_sort_keys),
                            max(evaluated_sort_keys),
                        )
                        diff = max_value - min_value
                        if diff > 0:
                            outputs = [
                                (value - min_value) / diff
                                for value in evaluated_sort_keys
                            ]
                    else:
                        if sort_key is not None:
                            order.sort(key=sort_key)

                        assert outputs is not None
                        for u, v in enumerate(order):
                            outputs[v] = u / (num_positions - 1)

            elif output_type == "INDEXED_BY_DRONES":
                # Gradient based on drone index
                if num_positions > 1:
                    np_m1 = num_positions - 1
                    outputs = [index / np_m1 for index in range(num_positions)]
                else:
                    common_output = 1.0

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
                    if None in mapping:
                        sorted_valid_mapping = sorted(
                            x for x in mapping if x is not None
                        )
                        np_m1 = max(len(sorted_valid_mapping) - 1, 1)
                        outputs = [
                            None if x is None else sorted_valid_mapping.index(x) / np_m1
                            for x in mapping
                        ]
                    # otherwise just normalize full mapping to [0, 1]
                    else:
                        np_m1 = max(num_positions - 1, 1)
                        outputs = [None if x is None else x / np_m1 for x in mapping]
                else:
                    # if there is no mapping at all, we do not change color of drones
                    outputs = [None] * num_positions  # type: ignore

            elif output_type == "CUSTOM":
                absolute_path = abspath(output_function.path)
                module = load_module(absolute_path) if absolute_path else None
                if self.output_function.name:
                    fn = getattr(module, self.output_function.name)
                    outputs = [
                        fn(
                            frame=frame,
                            time_fraction=time_fraction,
                            drone_index=index,
                            formation_index=(
                                mapping[index] if mapping is not None else None
                            ),
                            position=positions[index],
                            drone_count=num_positions,
                        )
                        for index in range(num_positions)
                    ]
                else:
                    common_output = 1.0

            else:
                # Should not get here
                common_output = 1.0

            return outputs, common_output

        # Do some quick checks to decide whether we need to bother at all
        if not self.enabled or not self.contains_frame(frame):
            return

        time_fraction = (frame - self.frame_start) / max(self.duration - 1, 1)
        num_positions = len(positions)

        color_ramp = self.color_ramp
        color_image = self.color_image
        color_function_ref = self.color_function_ref
        new_color = [0.0] * 4

        outputs_x, common_output_x = get_output_based_on_output_type(
            self.output, self.output_mapping_mode, self.output_function
        )
        if color_image is not None:
            outputs_y, common_output_y = get_output_based_on_output_type(
                self.output_y, self.output_mapping_mode_y, self.output_function_y
            )

        # Get the additional predicate required to evaluate whether the effect
        # will be applied at a given position
        condition = self._get_spatial_effect_predicate()

        for index, position in enumerate(positions):
            # Take the base color to modify
            color = colors[index]

            # Calculate the output value of the effect that goes through the color
            # ramp or image mapper
            if common_output_x is not None:
                output_x = common_output_x
            else:
                assert outputs_x is not None
                # if this specific output is disabled, we
                # skip the effect
                if outputs_x[index] is None:
                    continue
                output_x = outputs_x[index]
            assert isinstance(output_x, float)

            if color_image is not None:
                if common_output_y is not None:
                    output_y = common_output_y
                else:
                    assert outputs_y is not None
                    # if this specific output is disabled, we
                    # skip the effect
                    if outputs_y[index] is None:
                        continue
                    output_y = outputs_y[index]
                assert isinstance(output_y, float)

            # Randomize the output value if needed
            if self.randomness != 0:
                offset_x = (random_seq.get_float(index) - 0.5) * self.randomness
                output_x = (offset_x + output_x) % 1.0
                if color_image is not None:
                    offset_y = (random_seq.get_float(index) - 0.5) * self.randomness
                    output_y = (offset_y + output_y) % 1.0

            # Calculate the influence of the effect, depending on the fade-in
            # and fade-out durations and the optional mesh
            alpha = max(
                min(self._evaluate_influence_at(position, frame, condition), 1.0), 0.0
            )

            if color_function_ref is not None:
                try:
                    new_color[:] = color_function_ref(
                        frame=frame,
                        time_fraction=time_fraction,
                        drone_index=index,
                        formation_index=(
                            mapping[index] if mapping is not None else None
                        ),
                        position=position,
                        drone_count=num_positions,
                    )
                except Exception as exc:
                    raise RuntimeError("ERROR_COLOR_FUNCTION") from exc
            elif color_image is not None:
                width, height = color_image.size
                pixels = self.get_image_pixels()

                x = int((width - 1) * output_x)
                y = int((height - 1) * output_y)
                offset = (x + y * width) * 4
                pixel_color = pixels[offset : offset + 4]

                # This check is needed to cater for the cases when the calculated
                # pixel coordinate is out of the bounds of the image, in which
                # case get_pixel() returns an empty list or a short list
                if len(pixel_color) == len(new_color):
                    # If the conversion to linear space ever becomes a bottleneck,
                    # we can convert the image in advance when it is stored into
                    # the pixel cache if we can vectorize the operation somehow
                    # or offload it to C.
                    new_color[:] = convert_from_srgb_to_linear(pixel_color)  # type: ignore
            elif color_ramp:
                new_color[:] = color_ramp.evaluate(output_x)
            else:
                # should not happen
                new_color[:] = (1.0, 1.0, 1.0, 1.0)

            new_color[3] *= alpha

            # Apply the new color with alpha blending
            blend_in_place(new_color, color, BlendMode[self.blend_mode])  # type: ignore

    @property
    def color_ramp(self) -> Optional[ColorRamp]:
        """The color ramp of the effect, if it exists and is being used according
        to the type of the effect.
        """
        return self.texture.color_ramp if self.type == "COLOR_RAMP" else None

    @property
    def color_image(self) -> Optional[Image]:
        """The color image of the effect, if it exists and is being used according
        to the type of the effect.
        """
        return (
            self.texture.image
            if self.type == "IMAGE" and isinstance(self.texture, ImageTexture)
            else None
        )

    @color_image.setter
    def color_image(self, image: Optional[Image]):
        # If we have an old, legacy Texture instance, replace it with an
        # ImageTexture
        if not isinstance(self.texture, ImageTexture):
            self._remove_texture()
            self._create_texture()

        tex = self.texture
        if tex.image is not None:
            remove_if_unused(tex.image, from_=bpy.data.images)
        tex.image = image

        self.invalidate_color_image()

    @property
    def color_function_ref(self) -> Optional[Callable]:
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

    def create_color_image(self, name: str, width: int, height: int) -> Image:
        """Creates a new color image for the light effect (and deletes the old
        one if it already has one).

        Args:
            name: the name of the image to create
            width: the width of the image in pixels, corresponding to the
                time axis of the color animation
            height: the height of the image in pixels, corresponding to
                the number of drones to color

        Returns:
            the created color image itself for easy chaining
        """
        self.color_image = bpy.data.images.new(name=name, width=width, height=height)
        return self.color_image

    def get_image_pixels(self) -> Sequence[float]:
        """Returns the pixel-level representation of the color image of the light
        effect, caching the result for future use.
        """
        global _pixel_cache
        pixels = _pixel_cache.get(self.id)
        if pixels is None and self.color_image is not None:
            pixels = self.color_image.pixels[:]
            _pixel_cache.add(self.id, pixels, is_static=not self.is_animated)

        return pixels or ()

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
        self.target = other.target
        self.randomness = other.randomness
        self.output_mapping_mode = other.output_mapping_mode
        self.output_mapping_mode_y = other.output_mapping_mode_y
        self.blend_mode = other.blend_mode
        self.type = other.type
        self.color_image = other.color_image
        self.invert_target = other.invert_target

        self.color_function.update_from(other.color_function)
        self.output_function.update_from(other.output_function)
        self.output_function_y.update_from(other.output_function_y)

        if self.color_ramp is not None:
            assert other.color_ramp is not None  # because we copied the type
            update_color_ramp_from(self.color_ramp, other.color_ramp)

    def _evaluate_influence_at(
        self, position, frame: int, condition: Optional[Callable[[Coordinate3D], bool]]
    ) -> float:
        """Eveluates the effective influence of the effect on the given position
        in space and at the given frame.

        Parameters:
            position: the position to evaluate the influence at
            frame: the frame count
            condition: additional condition that must evaluate to true when called
                with the position; otherwise the effect will not be applied at all
        """
        # Apply mesh containment constraint
        if condition and not condition(position):
            return 0.0

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

        return influence

    def _get_bvh_tree_from_mesh(self) -> Optional[BVHTree]:
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
                with use_b_mesh() as b_mesh:
                    b_mesh.from_mesh(mesh.data)
                    b_mesh.transform(mesh.matrix_world)
                    tree = BVHTree.FromBMesh(b_mesh)
            return tree

    def _get_plane_from_mesh(self) -> Optional[Plane]:
        """Returns a plane that is an infinite expansion of the first face of the
        mesh associated to this light effect, or `None` if the light effect has
        no associated mesh or it has no faces.
        """
        if self.mesh:
            mesh = self.mesh.data
            local_to_world = self.mesh.matrix_world
            for polygon in mesh.polygons:
                normal = local_to_world.to_3x3() @ polygon.normal
                center = local_to_world @ polygon.center
                try:
                    return Plane.from_normal_and_point(normal, center)
                except Exception:
                    # probably all-zero normal vector
                    pass

    def _get_spatial_effect_predicate(self) -> Optional[Callable[[Coordinate3D], bool]]:
        if self.target == "INSIDE_MESH":
            bvh_tree = self._get_bvh_tree_from_mesh()
            func = partial(test_containment, bvh_tree)
        elif self.target == "FRONT_SIDE":
            plane = self._get_plane_from_mesh()
            func = partial(test_is_in_front_of, plane)
        else:
            func = None

        if self.invert_target:
            func = negate(func or _always_true)

        return func

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


class LightEffectCollection(PropertyGroup, ListMixin):
    """Blender property group representing the list of light effects to apply
    on the drones in the drone show.
    """

    #: The entries in the collection
    entries = CollectionProperty(type=LightEffect)

    #: Index of the active entry (currently being edited)
    active_entry_index = IntProperty(
        name="Selected index",
        description="Index of the light effect currently being edited",
    )

    @property
    def active_entry(self) -> Optional[LightEffect]:
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
        frame_start: Optional[int] = None,
        duration: Optional[int] = None,
        *,
        select: bool = False,
        context: Optional[Context] = None,
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

        entry: LightEffect = cast(LightEffect, self.entries.add())
        entry.type = "COLOR_RAMP"
        entry.frame_start = frame_start
        entry.duration = duration
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
        context: Optional[Context] = None,
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
        for entry in self.entries:
            if entry.enabled and entry.influence > 0 and entry.contains_frame(frame):
                yield entry

    def _on_removing_entry(self, entry) -> bool:
        entry._remove_texture()
        return True
