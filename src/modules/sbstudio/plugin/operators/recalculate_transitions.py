from typing import List, Optional, Sequence, Tuple

import bpy

from bpy.props import EnumProperty

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


class RecalculateTransitionsOperator(StoryboardOperator):
    """Recalculates all transitions in the show based on the current storyboard."""

    bl_idname = "skybrush.recalculate_transitions"
    bl_label = "Recalculate Transitions"
    bl_description = (
        "Recalculates all transitions in the show based on the current storyboard."
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
            end_of_scene = max(context.scene.frame_end, storyboard.frame_end)

            # Iterate through the entries for which we need to recalculate the
            # transitions
            for end_of_previous, entry, start_of_next in entry_info:
                self._update_transition_for_storyboard_entry(
                    entry,
                    drones,
                    get_positions_of=get_positions_of,
                    start_of_scene=start_of_scene,
                    end_of_previous=end_of_previous,
                    start_of_next=start_of_next,
                    end_of_scene=end_of_scene,
                )

        bpy.ops.skybrush.fix_constraint_ordering()

        invalidate_caches(clear_result=True)

        return {"FINISHED"}

    def _update_transition_for_storyboard_entry(
        self,
        entry,
        drones,
        *,
        get_positions_of,
        start_of_scene: int,
        end_of_previous: Optional[int],
        start_of_next: Optional[int],
        end_of_scene: int,
    ):
        """Updates the transition constraints corresponding to the given
        storyboard entry.

        Parameters:
            entry: the storyboard entry
            drones: the drones in the scene
            start_of_scene: the first frame of the scene
            start_of_next: the frame where the _next_ storyboard entry starts;
                `None` if this is the last storyboard entry
            end_of_previous: the frame where the _previous_ storyboard entry
                ended; `None` if this is the first storyboard entry
            end_of_scene: the last frame of the scene
        """
        formation = entry.formation
        if formation is None:
            # free segment, nothing to do here
            return

        if end_of_previous is None:
            end_of_previous = start_of_scene

        num_drones = len(drones)

        markers_and_objects = get_markers_and_related_objects_from_formation(formation)
        num_markers = len(markers_and_objects)

        # We need to create a transition between the places where the drones
        # are at the end of the previous formation and the points of the
        # current formation
        if entry.transition_type == "AUTO":
            # Auto mapping with our API
            source = get_positions_of(drones, frame=end_of_previous)
            target = [
                tuple(pos)
                for pos in get_world_coordinates_of_markers_from_formation(
                    formation, frame=entry.frame_start
                )
            ]
            try:
                match = get_api().match_points(source, target)
            except Exception:
                self.report(
                    {"ERROR"},
                    "Error while invoking transition planner on the Skybrush Studio online service",
                )
                return {"CANCELLED"}
            source, target = None, None
        else:
            # Manual mapping
            match = list(range(min(num_drones, num_markers)))
            if num_drones < num_markers:
                match.extend([None] * (num_markers - num_drones))

        # match[i] now contains the index of the drone that the i-th
        # target point was matched to. We need to invert the mapping.
        inverted_mapping = [None] * num_drones
        for target_index, source_index in enumerate(match):
            if source_index is not None:
                inverted_mapping[source_index] = target_index

        # Now we have the index of the target point that each drone
        # should be mapped to, and we have `None` for those drones that
        # will not participate in the formation
        for source_index, drone in enumerate(drones):
            target_index = inverted_mapping[source_index]
            constraint = find_transition_constraint_between(
                drone=drone, storyboard_entry=entry
            )

            if target_index is None:
                # This drone will not participate in this formation so
                # we need to delete the constraint that ties the drone
                # to the formation
                if constraint is not None:
                    drone.constraints.remove(constraint)
            else:
                # If we don't have a constraint between the drone
                # and the formation, create one
                if constraint is None:
                    constraint = create_transition_constraint_between(
                        drone=drone, storyboard_entry=entry
                    )
                else:
                    # Make sure that the name of the constraint contains the
                    # name of the formation even if the user renamed it
                    set_constraint_name_from_storyboard_entry(constraint, entry)

                # Set the target of the constraint to the appropriate
                # point of the formation
                marker, obj = markers_and_objects[target_index]
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

            if constraint is not None:
                # Construct the data path of the constraint we are going to
                # modify
                key = f"constraints[{constraint.name!r}].influence".replace("'", '"')

                # Create keyframes for the influence of the constraint
                ensure_action_exists_for_object(drone)

                # Decide the start and end time of the "windup" period of the
                # constraint where it gradually starts affecting the position
                # of the drone. This period must be somewhere between the end
                # of the previous formation and the start of the current
                # formation.
                windup_start = min(entry.frame_start - 1, end_of_previous)
                windup_end = entry.frame_start

                # Now construct the list of keyframes. We have to cater for
                # all sorts of edge cases as we need to ensure that no
                # keyframe X coordiate is repeated twice. Let's start with
                # specifying that the constraint must take no effect until the
                # end of the previous storyboard entry
                keyframes = [(windup_start, 0.0)]
                if start_of_scene < windup_start:
                    keyframes.insert(0, (start_of_scene, 0.0))

                # Now we declare that the constraint must take full effect
                # at the start of the storyboard entry and must keep on doing
                # so until the end of the storyboard entry
                keyframes.append((windup_end, 1.0))
                if entry.frame_end > entry.frame_start:
                    keyframes.append((entry.frame_end, 1.0))

                # If we have another formation that follows this one,
                # the influence of the constraint must stay until the next
                # formation starts, and then wind down
                if start_of_next is not None:
                    keyframes.append((start_of_next, 1.0))
                    keyframes.append((start_of_next + 1, 0.0))

                # The influence must become zero at the end of the scene if it
                # is later than the next formation
                if end_of_scene > keyframes[-1][0]:
                    keyframes.append((end_of_scene, 0.0))

                # Since 'keyframes' spans from the start of the scene to the
                # end, this will update all keyframes for the constraint.
                # We need this to handle cases when the user reorders the
                # formations.
                set_keyframes(
                    drone,
                    key,
                    keyframes,
                    clear_range=True,
                    interpolation="BEZIER",
                )

    def _get_transitions_to_process(
        self, storyboard: Storyboard, entries: Sequence[StoryboardEntry]
    ) -> List[Tuple[float, StoryboardEntry, float]]:
        """Processes the storyboard entries and selects the ones for which we
        need to recalculate the transitions, based on the scope parameter of
        the operator.

        Returns:
            for each entry where the transition _to_ the formation of the entry
            has to be recalculated, a tuple containing the end of the
            previous formation (`None` if this is the first formation in the
            entire storyboard), the storyboard entry itself, and the start frame
            of the next formation (`None` if this is the last formation in the
            entire storyboard)
        """
        entry_info = []
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

        for index, entry in enumerate(entries):
            if condition(index):
                entry_info.append(
                    (
                        None if index == 0 else entries[index - 1].frame_end,
                        entry,
                        None
                        if index == num_entries - 1
                        else entries[index + 1].frame_start,
                    )
                )

        return entry_info
