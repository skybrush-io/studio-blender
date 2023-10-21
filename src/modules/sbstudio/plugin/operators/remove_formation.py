from sbstudio.plugin.model.storyboard import get_storyboard
from sbstudio.plugin.objects import remove_objects

from .base import FormationOperator
from .remove_storyboard_entry import remove_constraints_for_storyboard_entry

__all__ = ("RemoveFormationOperator",)


class RemoveFormationOperator(FormationOperator):
    """Blender operator that removes the selected formation."""

    bl_idname = "skybrush.remove_formation"
    bl_label = "Remove Selected Formation"
    bl_description = "Remove the selected formation from the show"

    def execute_on_formation(self, formation, context):
        storyboard = get_storyboard(context)

        for entry in storyboard.entries:
            if entry.formation is formation:
                remove_constraints_for_storyboard_entry(entry)

        remove_objects(formation)

        return {"FINISHED"}
