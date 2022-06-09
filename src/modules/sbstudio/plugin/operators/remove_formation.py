import bpy

from sbstudio.plugin.objects import remove_objects

from .base import FormationOperator

__all__ = ("RemoveFormationOperator",)


class RemoveFormationOperator(FormationOperator):
    """Blender operator that removes the selected formation."""

    bl_idname = "skybrush.remove_formation"
    bl_label = "Remove Selected Formation"
    bl_description = "Remove the selected formation from the show"

    def execute_on_formation(self, formation, context):
        remove_objects(formation)

        # TODO(ntamas): we also need to remove any constraints that were related
        # to this formation

        return {"FINISHED"}
