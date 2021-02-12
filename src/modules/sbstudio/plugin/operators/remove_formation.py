import bpy

from sbstudio.plugin.selection import select_only

from .base import FormationOperator

__all__ = ("RemoveFormationOperator",)


class RemoveFormationOperator(FormationOperator):
    """Blender operator that removes the selected formation."""

    bl_idname = "skybrush.remove_formation"
    bl_label = "Remove Selected Formation"
    bl_description = "Remove the selected formation from the show"

    def execute_on_formation(self, formation, context):
        # TODO(ntamas): it would be nicer to keep the selection
        select_only(formation, context=context)
        bpy.ops.object.delete()
        bpy.data.collections.remove(formation)

        # TODO(ntamas): we also need to remove any constraints that were related
        # to this formation

        return {"FINISHED"}
