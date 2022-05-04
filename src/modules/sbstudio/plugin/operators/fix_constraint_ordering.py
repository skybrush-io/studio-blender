from sbstudio.plugin.constants import Collections
from sbstudio.plugin.transition import get_id_for_formation_constraint
from sbstudio.plugin.utils import sort_collection

from .base import StoryboardOperator

__all__ = ("FixConstraintOrderingOperator",)


class FixConstraintOrderingOperator(StoryboardOperator):
    """Fixes the ordering of transition constraints in the show if the user
    somehow managed to mess them up.

    Constraints must be ordered such that constraints for later formations come
    later in the constraint stack.
    """

    bl_idname = "skybrush.fix_constraint_ordering"
    bl_label = "Fix Ordering of Transition Constraints"
    bl_description = "Fixes the ordering of transition constraints in the show"

    only_with_valid_storyboard = True

    def execute_on_storyboard(self, storyboard, entries, context):
        # Get all the drones
        drones = Collections.find_drones().objects

        # Sort the constraints such that the ones corresponding to formations
        # that come later (in time) appear later in the constraint chain.
        formation_priority_map = {
            get_id_for_formation_constraint(entry): index
            for index, entry in enumerate(entries)
        }

        def key_function(constraint):
            return formation_priority_map.get(constraint.name, 100000)

        for drone in drones:
            sort_collection(drone.constraints, key=key_function)

        return {"FINISHED"}
