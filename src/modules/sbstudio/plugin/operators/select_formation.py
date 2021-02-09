from bpy.types import MeshVertex

from sbstudio.plugin.model.formation import get_markers_from_formation
from sbstudio.plugin.plugin_helpers import enter_edit_mode, temporarily_exit_edit_mode
from sbstudio.plugin.objects import object_contains_vertex
from sbstudio.plugin.selection import (
    add_to_selection,
    ensure_vertex_select_mode_enabled,
    remove_from_selection,
)

from .base import FormationOperator

__all__ = ("SelectFormationOperator", "DeselectFormationOperator")


class SelectFormationOperator(FormationOperator):
    """Blender operator that adds the selected formation to the selection."""

    bl_idname = "skybrush.select_formation"
    bl_label = "Select Formation"
    bl_description = "Adds the selected formation to the selection"

    def execute_on_formation(self, formation, context):
        # We need to update the selection in object mode; the edit mode works
        # with a temporary copy of the mesh so we can't change the selection
        # there
        with temporarily_exit_edit_mode():
            markers = get_markers_from_formation(formation)
            add_to_selection(markers, context=context)

        if all(isinstance(marker, MeshVertex) for marker in markers):
            # Formation consists of mesh vertices only so we should switch to
            # edit mode
            objects_of_markers = [
                obj
                for obj in formation.objects
                if any(object_contains_vertex(obj, marker) for marker in markers)
            ]
            if len(objects_of_markers) == 1:
                enter_edit_mode(objects_of_markers[0], context=context)
                ensure_vertex_select_mode_enabled(context=context)
            else:
                self.report(
                    {"ERROR"},
                    "This formation consists of multiple objects; cannot select one for Edit mode",
                )

        return {"FINISHED"}


class DeselectFormationOperator(FormationOperator):
    """Blender operator that removes the selected formation from the selection."""

    bl_idname = "skybrush.deselect_formation"
    bl_label = "Deselect Formation"
    bl_description = "Removes the selected formation from the selection"

    @classmethod
    def poll(cls, context):
        # We are currently disabling this operator in Edit mode because I could
        # not get it to work properly with vertex-based formations
        return context.mode != "EDIT_MESH" and super(
            DeselectFormationOperator, cls
        ).poll(context)

    def execute_on_formation(self, formation, context):
        with temporarily_exit_edit_mode():
            markers = get_markers_from_formation(formation)
            remove_from_selection(markers, context=context)
        return {"FINISHED"}
