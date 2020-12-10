from collections import defaultdict

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.errors import StoryboardValidationError
from sbstudio.plugin.transition import (
    create_transition_constraint_between,
    find_transition_constraint_between,
    is_transition_constraint,
)

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

        # For each drone, check whether there exists a constraint between the
        # drone and all the formations as outlined above. Add new constraints
        # for drone-formation pairs as needed, and remove unneeded drone-formation
        # constraints
        drones = Collections.find_drones().objects
        constraints_to_keep_by_drones = defaultdict(list)
        for formation in formations:
            # Skip empty formations
            if not len(formation.objects):
                continue

            for drone in drones:
                constraint = find_transition_constraint_between(
                    drone=drone, formation=formation
                )
                if constraint is None:
                    constraint = create_transition_constraint_between(
                        drone=drone, formation=formation
                    )
                else:
                    # TODO(ntamas): delete keyframes from constraint
                    pass

                constraints_to_keep_by_drones[drone].append(constraint)

        # For any formations that are _not_ in the selected ones, delete the
        # constraints between them and the drones
        for drone in drones:
            constraints_to_keep = constraints_to_keep_by_drones.get(drone, ())
            constraints_to_delete = []
            for constraint in drone.constraints:
                if (
                    is_transition_constraint(constraint)
                    and constraint not in constraints_to_keep
                ):
                    constraints_to_delete.append(constraint)

            for constraint in constraints_to_delete:
                drone.constraints.remove(constraint)

        return {"FINISHED"}
