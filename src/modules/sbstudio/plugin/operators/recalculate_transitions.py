from dataclasses import dataclass
from enum import Enum
from functools import partial
from math import inf
from typing import List, Optional, Sequence, Tuple

import bpy

from bpy.props import EnumProperty

from sbstudio.api.errors import SkybrushStudioAPIError
from sbstudio.plugin.actions import (
    ensure_action_exists_for_object,
)
from sbstudio.plugin.api import get_api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.keyframes import set_keyframes
from sbstudio.plugin.model.formation import (
    get_markers_and_related_objects_from_formation,
    get_world_coordinates_of_markers_from_formation,
)
from sbstudio.plugin.model.storyboard import Storyboard, StoryboardEntry
from sbstudio.plugin.tasks.safety_check import invalidate_caches
from sbstudio.plugin.transition import (
    create_transition_constraint_between,
    find_transition_constraint_between,
    set_constraint_name_from_storyboard_entry,
)
from sbstudio.plugin.utils import create_internal_id
from sbstudio.plugin.utils.evaluator import create_position_evaluator
from sbstudio.utils import constant

from .base import StoryboardOperator

__all__ = ("RecalculateTransitionsOperator",)


class InfluenceCurveTransitionType(Enum):
    """Possible types of a transition phase of an influence curve."""

    LINEAR = "linear"
    SMOOTH_FROM_LEFT = "smoothFromLeft"
    SMOOTH_FROM_RIGHT = "smoothFromRight"
    SMOOTH = "smooth"


@dataclass
class InfluenceCurveDescriptor:
    """Dataclass that describes how the influence curve of a constraint should
    look like.

    We currently work with one type of influence curve at the moment. The curve
    starts from zero at the start of the scene, stays zero until (and including)
    a _windup start frame_, then transitions to 1 until (and including) a
    _start frame_. The transition can be linear, smooth from the left,
    smooth from the right or completely smooth. The curve will then either stay
    1 indefinitely, or stay 1 until a designated _end frame_, and then jump
    straight back to zero.

    The key points of the influence curve are described by this data class. It
    also provides a method to apply these points to an existing constraint.
    """

    scene_start_frame: int
    """The start frame of the entire scene."""

    windup_start_frame: Optional[int]
    """The windup start frame, i.e. the _last_ frame when the influence curve
    should still be zero before winding up to full influence. `None` means that
    it is the same as the start frame of the scene.

    When this frame is earlier than the start frame of the scene, it is assumed
    to be equal to the start frame of the scene.
    """

    start_frame: int
    """The first frame when the influence should become equal to 1. Must be
    larger than the windup start frame; when it is smaller or equal, it is
    assumed to be one larger than the windup start frame.
    """

    end_frame: Optional[int] = None
    """The last frame when the influence is still equal to 1; ``None`` means
    that the influence curve stays 1 infinitely.

    The end frame must be larger than or equal to the start frame; when it is
    smaller, it is assumed to be equal to the start frame.
    """

    windup_type: InfluenceCurveTransitionType = InfluenceCurveTransitionType.SMOOTH
    """The type of the windup transition."""

    def apply(self, object, data_path: str) -> None:
        """Applies the influence curve descriptor to the given data path of the
        given Blender object by updating the keyframes appropriately.

        Parameters:
            object: the object on which the keyframes are to be set
            data_path: the data path to use
        """
        keyframes: List[Tuple[int, float]] = [(self.scene_start_frame, 0.0)]
        if (
            self.windup_start_frame is not None
            and self.windup_start_frame > self.scene_start_frame
        ):
            keyframes.append((self.windup_start_frame, 0.0))

        frame = max(self.start_frame, keyframes[-1][0] + 1)
        start_of_transition = len(keyframes) - 1
        keyframes.append((frame, 1.0))

        if self.end_frame is not None:
            end_frame = max(self.end_frame, frame)
            if end_frame > frame:
                keyframes.append((end_frame, 1.0))

            keyframes.append((end_frame + 1, 0.0))

        keyframe_objs = set_keyframes(
            object,
            data_path,
            keyframes,
            clear_range=(None, inf),
            interpolation="LINEAR",
        )

        if self.windup_type != InfluenceCurveTransitionType.LINEAR:
            kf = keyframe_objs[start_of_transition]
            kf.interpolation = "BEZIER"
            if self.windup_type == InfluenceCurveTransitionType.SMOOTH_FROM_RIGHT:
                kf.handle_right_type = "VECTOR"
            else:
                kf.handle_right_type = "AUTO_CLAMPED"
            if self.windup_type == InfluenceCurveTransitionType.SMOOTH_FROM_LEFT:
                kf.handle_left_type = "VECTOR"
            else:
                kf.handle_left_type = "AUTO_CLAMPED"


class RecalculateTransitionsOperator(StoryboardOperator):
    """Recalculates all transitions in the show based on the current storyboard."""

    bl_idname = "skybrush.recalculate_transitions"
    bl_label = "Recalculate Transitions"
    bl_description = (
        "Recalculates all transitions in the show based on the current storyboard"
    )
    bl_options = {"UNDO"}

    scope = EnumProperty(
        items=[
            ("ALL", "Entire storyboard", "", "SEQUENCE", 1),
            ("CURRENT_FRAME", "Current frame", "", "EMPTY_SINGLE_ARROW", 2),
            None,
            (
                "TO_SELECTED",
                "To selected formation",
                "",
                "TRACKING_BACKWARDS_SINGLE",
                3,
            ),
            (
                "FROM_SELECTED",
                "From selected formation",
                "",
                "TRACKING_FORWARDS_SINGLE",
                4,
            ),
            (
                "FROM_SELECTED_TO_END",
                "From selected formation to end",
                "",
                "TRACKING_FORWARDS",
                5,
            ),
        ],
        name="Scope",
        description="Scope of the operator that defines which transitions must be recalculated",
        default="ALL",
    )

    only_with_valid_storyboard = True

    def execute_on_storyboard(self, storyboard, entries, context):
        # Get all the drones
        drones = Collections.find_drones().objects

        # If there are no drones, show a reasonable error message to the user
        if not drones:
            self.report({"ERROR"}, "You need to create some drones first")
            return {"CANCELLED"}

        # Prepare a list consisting of triplets like this:
        # end of previous formation, formation, start of next formation
        entry_info = self._get_transitions_to_process(storyboard, entries)
        if not entry_info:
            self.report({"ERROR"}, "No transitions match the selected scope")
            return {"CANCELLED"}

        with create_position_evaluator() as get_positions_of:
            # Grab some common constants that we will need
            start_of_scene = min(context.scene.frame_start, storyboard.frame_start)

            # Iterate through the entries for which we need to recalculate the
            # transitions
            for previous_entry, entry, start_of_next in entry_info:
                self._update_transition_for_storyboard_entry(
                    entry,
                    drones,
                    get_positions_of=get_positions_of,
                    previous_entry=previous_entry,
                    start_of_scene=start_of_scene,
                    start_of_next=start_of_next,
                )

        bpy.ops.skybrush.fix_constraint_ordering()

        invalidate_caches(clear_result=True)

        return {"FINISHED"}

    def _calculate_mapping_for_storyboard_entry(
        self, entry: StoryboardEntry, drones, *, num_targets: int, get_positions_of
    ) -> List[Optional[int]]:
        """Calculates the mapping of drones and positions for a storyboard
        entry.

        This function must be called only if the storyboard entry contains a
        formation (i.e. it is not a free segment).

        Parameters:
            entry: the storyboard entry
            drones: the drones to consider
            num_targets: number of target points that the drones should be
                mapped to; used for manual mapping so we can avoid querying
                all the coordinates if they are not needed
            get_positions_of: a callable that can be called with the list of
                drones and that returns the current coordinates of the drones

        Returns:
            a list where the i-th element contains the index of the target point
            that the i-th drone was matched to, or ``None`` if the drone was
            left unmatched

        Raises:
            SkybrushStudioAPIError: if an error happens while querying the
                remote API that calculates the mapping
        """
        formation = entry.formation
        if formation is None:
            raise RuntimeError(
                "mapping function called for storyboard entry with no formation"
            )

        num_drones = len(drones)

        result: List[Optional[int]] = [None] * num_drones

        # We need to create a transition between the places where the drones
        # are at the end of the previous formation and the points of the
        # current formation
        if entry.transition_type == "AUTO":
            # Auto mapping with our API
            source = get_positions_of(drones)
            target = [
                tuple(pos)
                for pos in get_world_coordinates_of_markers_from_formation(
                    formation, frame=entry.frame_start
                )
            ]
            try:
                match = get_api().match_points(source, target)
            except Exception as ex:
                if not isinstance(ex, SkybrushStudioAPIError):
                    raise SkybrushStudioAPIError from ex
                else:
                    raise

            # At this point we have the inverse mapping: match[i] tells the
            # index of the drone that the i-th target point was matched to, or
            # ``None`` if the target point was left unmatched. We need to invert
            # the mapping
            for target_index, drone_index in enumerate(match):
                if drone_index is not None:
                    result[drone_index] = target_index

        else:
            # Manual mapping
            length = min(num_drones, num_targets)
            result[:length] = range(length)

        return result

    def _update_transition_constraint_influence(
        self, drone, constraint, descriptor: InfluenceCurveDescriptor
    ) -> None:
        """Updates the F-curve of the influence parameter of the constraint that
        attaches a given drone to the formation of a given storyboard entry.

        Parameters:
            drone: the drone that the transition constraint affects
            entry: the storyboard entry corresponding to the constraint
            descriptor: the descriptor that describes how the influence F-curve
                should look like
        """
        # Construct the data path of the constraint we are going to
        # modify
        key = f"constraints[{constraint.name!r}].influence".replace("'", '"')

        # Create keyframes for the influence of the constraint
        ensure_action_exists_for_object(drone)

        # Apply the influence curve to the drone
        descriptor.apply(drone, key)

    def _update_transition_constraint_properties(
        self, drone, entry: StoryboardEntry, marker, obj
    ):
        """Updates the constraint that attaches a drone to its target in the
        transition.

        Parameters:
            drone: the drone to update
            entry: the storyboard entry; it will be used to select the appropriate
                constraint that corresponds to the drone _and_ the entry
            marker: the marker that the drone will be transitioning to; ``None``
                if the drone is not matched to a target in this transition
            obj: the parent mesh of the marker if the marker is a vertex in a
                Blender mesh, or the marker itself if the marker is a target
                mesh on its own (typically a Blender empty object)

        Returns:
            the Blender constraint that corresponds to the drone and the
            storyboard entry, or ``None`` if no such constraint is needed
            because the drone is unmatched
        """
        constraint = find_transition_constraint_between(
            drone=drone, storyboard_entry=entry
        )
        if marker is None:
            # This drone will not participate in this formation so
            # we need to delete the constraint that ties the drone
            # to the formation
            if constraint is not None:
                drone.constraints.remove(constraint)
            return None

        # If we don't have a constraint between the drone and the storyboard
        # entry, create one
        if constraint is None:
            constraint = create_transition_constraint_between(
                drone=drone, storyboard_entry=entry
            )
        else:
            # Make sure that the name of the constraint contains the
            # name of the formation even if the user renamed it
            set_constraint_name_from_storyboard_entry(constraint, entry)

        # Set the target of the constraint to the appropriate point of the
        # formation
        if marker is obj:
            # The marker itself is an object so it can be a constraint
            # target on its own
            constraint.target = marker
        else:
            # The marker is a vertex in a mesh so we need to create or
            # find a vertex group that contains the vertex only, and
            # use the vertex group as a subtarget
            index = marker.index
            vertex_group_name = create_internal_id(f"Vertex {index}")
            vertex_groups = obj.vertex_groups
            try:
                vertex_group = vertex_groups[vertex_group_name]
            except KeyError:
                # No such group, let's create it
                vertex_group = vertex_groups.new(name=vertex_group_name)

            # Ensure that the vertex group contains the target vertex
            # only in case the mesh was modified. Let's hope that
            # Blender is smart enough to make this a no-op if the vertex
            # group is okay as-is
            vertex_group.add([index], 1, "REPLACE")

            constraint.target = obj
            constraint.subtarget = vertex_group_name

        return constraint

    def _update_transition_for_storyboard_entry(
        self,
        entry: StoryboardEntry,
        drones,
        *,
        get_positions_of,
        previous_entry: Optional[StoryboardEntry],
        start_of_scene: int,
        start_of_next: Optional[int],
    ):
        """Updates the transition constraints corresponding to the given
        storyboard entry.

        Parameters:
            entry: the storyboard entry
            previous_entry: the storyboard entry that precedes the given entry;
                `None` if the given entry is the first one
            drones: the drones in the scene
            start_of_scene: the first frame of the scene
            start_of_next: the frame where the _next_ storyboard entry starts;
                `None` if this is the last storyboard entry
        """
        formation = entry.formation
        if formation is None:
            # free segment, nothing to do here
            return

        markers_and_objects = get_markers_and_related_objects_from_formation(formation)
        num_markers = len(markers_and_objects)
        end_of_previous = previous_entry.frame_end if previous_entry else start_of_scene

        try:
            mapping = self._calculate_mapping_for_storyboard_entry(
                entry,
                drones,
                num_targets=num_markers,
                get_positions_of=partial(get_positions_of, frame=end_of_previous),
            )
        except SkybrushStudioAPIError:
            self.report(
                {"ERROR"},
                "Error while invoking transition planner on the Skybrush Studio online service",
            )
            return {"CANCELLED"}

        # Calculate how many drones will participate in the transition
        num_drones_transitioning = sum(
            1 for target_index in mapping if target_index is not None
        )

        # Now we have the index of the target point that each drone
        # should be mapped to, and we have `None` for those drones that
        # will not participate in the formation
        for source_index, drone in enumerate(drones):
            target_index = mapping[source_index]
            if target_index is None:
                marker, obj = None, None
            else:
                marker, obj = markers_and_objects[target_index]

            constraint = self._update_transition_constraint_properties(
                drone, entry, marker, obj
            )

            if constraint is not None:
                # windup_start_frame can be later than end_of_previous for
                # staggered departures.

                windup_start_frame = end_of_previous
                start_frame = entry.frame_start
                if entry.is_staggered:
                    windup_start_frame += (
                        entry.pre_delay_per_drone_in_frames * source_index
                    )
                    start_frame -= entry.post_delay_per_drone_in_frames * (
                        num_drones_transitioning - source_index - 1
                    )

                # start_frame can be earlier than entry.frame_start for
                # staggered arrivals.
                descriptor = InfluenceCurveDescriptor(
                    scene_start_frame=start_of_scene,
                    windup_start_frame=windup_start_frame,
                    start_frame=start_frame,
                    end_frame=start_of_next,
                )
                self._update_transition_constraint_influence(
                    drone, constraint, descriptor
                )

    def _get_transitions_to_process(
        self, storyboard: Storyboard, entries: Sequence[StoryboardEntry]
    ) -> List[Tuple[Optional[StoryboardEntry], StoryboardEntry, Optional[int]]]:
        """Processes the storyboard entries and selects the ones for which we
        need to recalculate the transitions, based on the scope parameter of
        the operator.

        Returns:
            for each entry where the transition _to_ the formation of the entry
            has to be recalculated, a tuple containing the previous storyboard
            entry (`None` if this is the first formation in the entire
            storyboard), the current storyboard entry, and the start frame of
            the next formation (`None` if this is the last formation in the
            entire storyboard)
        """
        entry_info: List[
            Tuple[Optional[StoryboardEntry], StoryboardEntry, Optional[int]]
        ] = []
        active_index = int(storyboard.active_entry_index)
        num_entries = len(entries)

        if self.scope == "FROM_SELECTED":
            condition = (
                (active_index + 1).__eq__
                if active_index < num_entries - 1
                else constant(False)
            )
        elif self.scope == "TO_SELECTED":
            condition = active_index.__eq__
        elif self.scope == "FROM_SELECTED_TO_END":
            condition = active_index.__le__
        elif self.scope == "CURRENT_FRAME":
            frame = bpy.context.scene.frame_current
            index = storyboard.get_index_of_entry_after_frame(frame)
            condition = index.__eq__
        elif self.scope == "ALL":
            condition = constant(True)
        else:
            condition = constant(False)

        prev_entry: Optional[StoryboardEntry] = None
        for index, entry in enumerate(entries):
            if condition(index):
                entry_info.append(
                    (
                        prev_entry,
                        entry,
                        None
                        if index == num_entries - 1
                        else entries[index + 1].frame_start,
                    )
                )
            prev_entry = entry

        return entry_info
