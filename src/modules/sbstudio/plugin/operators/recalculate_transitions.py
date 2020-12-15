from sbstudio.plugin.actions import (
    ensure_action_exists_for_object,
    find_f_curve_for_data_path,
)
from sbstudio.plugin.api import api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.keyframes import set_keyframes
from sbstudio.plugin.model.formation import get_all_markers_from_formation
from sbstudio.plugin.transition import (
    create_transition_constraint_between,
    find_transition_constraint_between,
)
from sbstudio.plugin.utils.evaluator import create_position_evaluator

from .base import StoryboardOperator

__all__ = ("RecalculateTransitionsOperator",)


class RecalculateTransitionsOperator(StoryboardOperator):
    """Recalculates all transitions in the show based on the current storyboard."""

    bl_idname = "skybrush.recalculate_transitions"
    bl_label = "Recalculate Transitions"
    bl_description = (
        "Recalculates all transitions in the show based on the current storyboard."
    )

    def execute_on_storyboard(self, storyboard, context):
        try:
            entries = storyboard.validate_and_sort_entries()
        except StoryboardValidationError as ex:
            self.report({"ERROR_INVALID_INPUT"}, str(ex))
            return {"CANCELLED"}

        # Get all the drones
        drones = Collections.find_drones().objects

        # Get hold of a function to jump to a given frame
        seek_to = context.scene.frame_set

        # Prepare a list consisting of triplets like this:
        # end of previous formation, formation, start of next formation
        num_entries = len(entries)
        entry_info = []
        for index, entry in enumerate(entries):
            entry_info.append(
                (
                    None if index == 0 else entries[index - 1].frame_end,
                    entry,
                    None
                    if index == num_entries - 1
                    else entries[index + 1].frame_start,
                )
            )

        with create_position_evaluator() as get_positions_of:
            # Iterate through the storyboard
            for end_of_previous, entry, start_of_next in entry_info:
                formation = entry.formation
                if formation is None:
                    # free segment, nothing to do here
                    continue

                is_first_formation = end_of_previous is None
                if end_of_previous is None:
                    end_of_previous = context.scene.frame_start

                markers = get_all_markers_from_formation(formation)

                # We need to create a transition between the places where the drones
                # are at the end of the previous formation and the points of the
                # current formation
                source = get_positions_of(drones, frame=end_of_previous)
                target = get_positions_of(markers, frame=entry.frame_start)
                match = api.match_points(source, target)

                # match[i] now contains the index of the drone that the i-th
                # target point was matched to. We need to invert the mapping.
                inverted_mapping = [None] * len(source)
                for target_index, source_index in enumerate(match):
                    if source_index is not None:
                        inverted_mapping[source_index] = target_index

                # Now we have the index of the target point that each drone
                # should be mapped to, and we have `None` for those drones that
                # will not participate in the formation
                for source_index, drone in enumerate(drones):
                    target_index = inverted_mapping[source_index]
                    constraint = find_transition_constraint_between(
                        drone=drone, formation=formation
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
                                drone=drone, formation=formation
                            )

                        # Set the target of the constraint to the appropriate
                        # point of the formation
                        constraint.target = markers[target_index]

                    # Construct the data path of the constraint we are going to
                    # modify
                    key = f"constraints[{constraint.name!r}].influence".replace(
                        "'", '"'
                    )

                    # Create keyframes for the influence of the constraint
                    ensure_action_exists_for_object(drone)
                    keyframes = [
                        (end_of_previous, 0.0),
                        (entry.frame_start, 1.0),
                        (entry.frame_end, 1.0),
                    ]
                    if start_of_next is not None:
                        keyframes.append((start_of_next, 0.0))
                    new_keyframe_points = set_keyframes(drone, key, keyframes)

                    # For the first formation, the takeoff should be abrupt,
                    # not smooth, so tweak the keyframe a bit
                    if is_first_formation:
                        transition_duration = entry.frame_start - end_of_previous
                        new_keyframe_points[0].handle_right = (
                            transition_duration * 0.25,
                            0.25,
                        )

        # TODO(ntamas): sort the constraints such that the ones corresponding
        # to formations that come later (in time) appear later in the constraint
        # chain. Right now it doesn't cause any problems, but it would be nicer
        # for the user as it would be easier to find a particular constraint.

        # TODO(ntamas): currently it is not possible for a formation to appear
        # more than once in the sequence

        return {"FINISHED"}
