import bpy
import bmesh

from functools import partial
from operator import itemgetter
from typing import Callable, Iterable, List, Optional, Sequence

from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import ColorRamp, Context, PropertyGroup, Mesh, Object, Texture
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from sbstudio.math.rng import RandomSequence
from sbstudio.model.plane import Plane
from sbstudio.model.types import Coordinate3D, RGBAColor
from sbstudio.plugin.constants import DEFAULT_LIGHT_EFFECT_DURATION
from sbstudio.plugin.utils import remove_if_unused, with_context
from sbstudio.plugin.utils.color_ramp import update_color_ramp_from
from sbstudio.plugin.utils.evaluator import get_position_of_object
from sbstudio.utils import alpha_over_in_place, distance_sq_of

from .mixins import ListMixin

__all__ = ("LightEffect", "LightEffectCollection")


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


class LightEffect(PropertyGroup):
    """Blender property group representing a single, time- and possibly space-limited
    light effect in the drone show.
    """

    # If you add new properties below, make sure to update update_from()

    enabled = BoolProperty(
        name="Enabled",
        description="Whether this light effect is enabled",
        default=True,
        options=set(),
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
        default=0,
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
        name="Output",
        description="Output function that determines the value that is passed through the color ramp to obtain the color to assign to a drone",
        items=[
            ("FIRST_COLOR", "First color of color ramp", "", 1),
            ("LAST_COLOR", "Last color of color ramp", "", 2),
            ("INDEXED", "Gradient", "", 3),
            ("GRADIENT_XYZ", "Gradient (XYZ)", "", 4),
            ("GRADIENT_XZY", "Gradient (XZY)", "", 5),
            ("GRADIENT_YXZ", "Gradient (YXZ)", "", 6),
            ("GRADIENT_YZX", "Gradient (YZX)", "", 7),
            ("GRADIENT_ZXY", "Gradient (ZXY)", "", 8),
            ("GRADIENT_ZYX", "Gradient (ZYX)", "", 9),
            ("TEMPORAL", "Temporal", "", 10),
            ("DISTANCE", "Distance from mesh", "", 11),
            ("CUSTOM", "Custom expression", "", 12),
        ],
        default="LAST_COLOR",
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
        description="Texture of the light effect, used for the sole purpose of having a way to create a color ramp",
        options={"HIDDEN"},
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
            " to those drones that are inside the given mesh"
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
            "Offsets the output value of each drone randomly on the color ramp; this property defines the maximum value of the offset"
        ),
        default=0,
        min=0,
        soft_min=0,
        soft_max=1,
        precision=2,
        options=set(),
    )

    # If you add new properties above, make sure to update update_from()

    def apply_on_colors(
        self,
        colors: Sequence[RGBAColor],
        positions: Sequence[Coordinate3D],
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
            frame: the frame index
            random_seq: a random sequence that is used to spread out the items
                on the color ramp if randomization is turned on
        """
        # Do some quick checks to decide whether we need to bother at all
        if not self.enabled or not self.contains_frame(frame):
            return

        num_positions = len(positions)

        output_type: str = self.output
        color_ramp = self.color_ramp
        new_color = [0.0] * 4
        order: Optional[List[int]] = None

        outputs: Optional[List[float]] = None
        common_output: Optional[float] = None

        if output_type == "FIRST_COLOR":
            common_output = 0.0
        elif output_type == "LAST_COLOR":
            common_output = 1.0
        elif output_type == "TEMPORAL":
            common_output = (frame - self.frame_start) / self.duration
        elif output_type.startswith("GRADIENT_") or output_type == "DISTANCE":
            if output_type == "DISTANCE":
                if self.mesh:
                    position_of_mesh = get_position_of_object(self.mesh)
                    sort_key = lambda index: distance_sq_of(
                        positions[index], position_of_mesh
                    )
                else:
                    sort_key = None
            else:
                query_axes = (
                    OUTPUT_TYPE_TO_AXIS_SORT_KEY.get(output_type)
                    or OUTPUT_TYPE_TO_AXIS_SORT_KEY["default"]
                )
                sort_key = lambda index: query_axes(positions[index])

            order = list(range(num_positions))
            if sort_key is not None:
                order.sort(key=sort_key)

            outputs = [1.0] * num_positions
            if num_positions > 1:
                for u, v in enumerate(order):
                    outputs[v] = u / (num_positions - 1)
        elif output_type == "INDEXED":
            # Gradient based on index
            if num_positions > 1:
                np_m1 = num_positions - 1
                outputs = [index / np_m1 for index in range(num_positions)]
            else:
                common_output = 1.0
        elif output_type == "CUSTOM_EXPRESSION":
            # TODO(ntamas)
            common_output = 1.0
        else:
            # Should not get here
            common_output = 1.0

        # Get the additional predicate required to evaluate whether the effect
        # will be applied at a given position
        condition = self._get_spatial_effect_predicate()

        for index, position in enumerate(positions):
            # Take the base color to modify
            color = colors[index]

            # Calculate the output value of the effect that goes through the color
            # ramp mapper
            if common_output is not None:
                output = common_output
            else:
                assert outputs is not None
                output = outputs[index]

            # Randomize the output value if needed
            if self.randomness != 0:
                offset = (random_seq.get_float(index) - 0.5) * self.randomness
                output = (offset + output) % 1.0

            # Calculate the influence of the effect, depending on the fade-in
            # and fade-out durations and the optional mesh
            alpha = max(
                min(self._evaluate_influence_at(position, frame, condition), 1.0), 0.0
            )

            if color_ramp:
                new_color[:] = color_ramp.evaluate(output)
                new_color[3] *= alpha
            else:
                # should not happen
                new_color[:] = (1.0, 1.0, 1.0, alpha)

            # Apply the new color with alpha blending
            alpha_over_in_place(new_color, color)  # type: ignore

    @property
    def color_ramp(self) -> Optional[ColorRamp]:
        """The color ramp of the effect."""
        return self.texture.color_ramp if self.texture else None

    def contains_frame(self, frame: int) -> bool:
        """Returns whether the light effect contains the given frame.

        Storyboard entries are closed from the left and open from the right;
        in other words, they always contain their start frames but they do not
        contain their end frames.
        """
        return 0 <= (frame - self.frame_start) < self.duration

    @property
    def frame_end(self) -> int:
        """Returns the index of the last frame that is covered by the effect."""
        return self.frame_start + self.duration

    def update_from(self, other: "LightEffect") -> None:
        """Updates the properties of this light effect from another one,
        _except_ its name.
        """
        self.enabled = other.enabled
        self.frame_start = other.frame_start
        self.duration = other.duration
        self.fade_in_duration = other.fade_in_duration
        self.fade_out_duration = other.fade_out_duration
        self.output = other.output
        self.influence = other.influence
        self.mesh = other.mesh
        self.target = other.target
        self.randomness = other.randomness

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
        if self.mesh:
            b_mesh = bmesh.new()
            b_mesh.from_mesh(self.mesh.data)
            b_mesh.transform(self.mesh.matrix_world)
            tree = BVHTree.FromBMesh(b_mesh)
            b_mesh.free()
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
            return partial(test_containment, bvh_tree)
        elif self.target == "FRONT_SIDE":
            plane = self._get_plane_from_mesh()
            return partial(test_is_in_front_of, plane)


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
            duration: the duration of the new entry; `None` chooses a sensible
                default
            select: whether to select the newly added entry after it was created
        """
        scene = context.scene

        fps = scene.render.fps
        if frame_start is None:
            # TODO(ntamas): choose the start of the formation that includes the
            # current frame or transition
            frame_start = scene.frame_start

        if duration is None or duration <= 0:
            duration = fps * DEFAULT_LIGHT_EFFECT_DURATION

        entry = self.entries.add()
        entry.frame_start = frame_start
        entry.duration = duration
        entry.name = name

        entry.texture = bpy.data.textures.new(
            name="Texture for light effect", type="NONE"
        )
        entry.texture.use_color_ramp = True

        # Clear alpha from color ramp
        elts = entry.texture.color_ramp.elements
        for elt in elts:
            elt.color[3] = 1.0

        # Copy default colors from the LED Control panel
        if hasattr(scene, "skybrush") and hasattr(scene.skybrush, "led_control"):
            led_control = scene.skybrush.led_control
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

        entry = self.append_new_entry(name=f"Copy of {active_entry.name}")
        entry.update_from(active_entry)
        self.entries.move(len(self.entries) - 1, index + 1)

        if select:
            self.active_entry_index = index + 1

        return entry

    @property
    def frame_end(self) -> int:
        """Returns the index of the last frame that is covered by light effects."""
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
        remove_if_unused(entry.texture, from_=bpy.data.textures)
        return True
