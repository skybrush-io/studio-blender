from sbstudio.plugin.actions import (
    ensure_action_exists_for_object,
)
from sbstudio.plugin.api import get_api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.keyframes import set_keyframes
from sbstudio.plugin.model.formation import get_all_markers_from_formation
from sbstudio.plugin.transition import (
    create_transition_constraint_between,
    find_transition_constraint_between,
    get_id_for_formation_constraint,
    set_constraint_name_from_formation,
)
from sbstudio.plugin.utils.evaluator import create_position_evaluator
from sbstudio.utils import get_moves_required_to_sort_collection

from .base import StoryboardOperator

__all__ = ("RecalculateTransitionsOperator",)


def sort_constraints_of_object(object, key):
    constraints = object.constraints
    moves = get_moves_required_to_sort_collection(constraints, key)
    for source, target in moves:
        constraints.move(source, target)


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
            # Grab some common constants that we will need
            start_of_scene = min(context.scene.frame_start, storyboard.frame_start)
            end_of_scene = max(context.scene.frame_end, storyboard.frame_end)

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

                if entry.transition_type == "AUTO":
                    # Auto mapping with our API
                    match = get_api().match_points(source, target)
                else:
                    # Manual mapping
                    match = list(range(min(len(source), len(target))))
                    if len(match) < len(target):
                        match.extend([None] * (len(target) - len(match)))

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
                        else:
                            # Make sure that the name of the constraint contains the
                            # name of the formation even if the user renamed it
                            set_constraint_name_from_formation(constraint, formation)

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
                        (start_of_scene, 0.0),
                        (end_of_previous, 0.0),
                        (entry.frame_start, 1.0),
                        (entry.frame_end, 1.0),
                    ]
                    if start_of_scene == end_of_previous:
                        del keyframes[0:1]
                    if start_of_next is not None:
                        keyframes.append((start_of_next, 1.0))
                        keyframes.append((start_of_next + 1, 0.0))
                        keyframes.append((end_of_scene, 0.0))

                    # Since 'keyframes' spans from the start of the scene to the
                    # end, this will update all keyframes for the constraint.
                    # We need this to handle cases when the user reorders the
                    # formations.
                    new_keyframe_points = set_keyframes(
                        drone, key, keyframes, clear_range=True
                    )

                    # For the first formation, the takeoff should be abrupt,
                    # not smooth, so tweak the keyframe a bit
                    if is_first_formation:
                        transition_duration = entry.frame_start - end_of_previous
                        new_keyframe_points[0].handle_right = (
                            transition_duration * 0.25,
                            0.25,
                        )

        # Sort the constraints such that the ones corresponding to formations
        # that come later (in time) appear later in the constraint chain.
        formation_priority_map = {
            get_id_for_formation_constraint(entry.formation): index
            for index, entry in enumerate(entries)
            if entry.formation is not None
        }

        def key_function(constraint):
            return formation_priority_map.get(constraint.name, 100000)

        for drone in drones:
            sort_constraints_of_object(drone, key=key_function)

        # TODO(ntamas): currently it is not possible for a formation to appear
        # more than once in the sequence

        return {"FINISHED"}
