from collections import defaultdict

from sbstudio.plugin.api import api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.model.formation import get_all_markers_from_formation
from sbstudio.plugin.transition import (
    create_transition_constraint_between,
    find_transition_constraint_between,
    is_transition_constraint,
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

        # Collect the formations that will need constraints between them and
        # the drones
        formations = set(entry.formation for entry in entries) - {None}

        # Create a variable that stores the time when the previous formation of
        # the storyboard ended
        end_of_previous_formation = context.scene.frame_start

        # Get all the drones
        drones = Collections.find_drones().objects

        with create_position_evaluator() as get_positions_of:
            # Iterate through the storyboard
            for entry in entries:
                formation = entry.formation
                markers = get_all_markers_from_formation(formation)

                # We need to create a transition between the places where the drones
                # are at the end of the previous formation and the points of the
                # current formation
                source = get_positions_of(drones, frame=end_of_previous_formation)
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

        return {"FINISHED"}
