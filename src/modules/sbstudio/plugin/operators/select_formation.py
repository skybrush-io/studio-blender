from sbstudio.plugin.model.formation import get_all_markers_from_formation
from sbstudio.plugin.selection import add_to_selection, remove_from_selection

from .base import FormationOperator

__all__ = ("SelectFormationOperator", "DeselectFormationOperator")


class SelectFormationOperator(FormationOperator):
    """Blender operator that adds the selected formation to the selection."""

    bl_idname = "skybrush.select_formation"
    bl_label = "Select Formation"
    bl_description = "Adds the selected formation to the selection"

    def execute_on_formation(self, formation, context):
        markers = get_all_markers_from_formation(formation)
        add_to_selection(markers)
        return {"FINISHED"}


class DeselectFormationOperator(FormationOperator):
    """Blender operator that removes the selected formation from the selection."""

    bl_idname = "skybrush.deselect_formation"
    bl_label = "Deselect Formation"
    bl_description = "Removes the selected formation from the selection"

    def execute_on_formation(self, formation, context):
        markers = get_all_markers_from_formation(formation)
        remove_from_selection(markers)
        return {"FINISHED"}
