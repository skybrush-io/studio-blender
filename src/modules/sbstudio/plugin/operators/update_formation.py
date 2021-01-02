import bpy

from bpy.props import EnumProperty
from mathutils import Vector

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.formation import (
    add_markers_to_formation,
    get_all_markers_from_formation,
)
from sbstudio.plugin.selection import (
    get_selected_objects,
    get_selected_vertices_grouped_by_objects,
    select_only,
)

from .base import FormationOperator

__all__ = ("UpdateFormationOperator",)


def get_options_for_formation_update():
    """Returns a list containing the options that we support in the
    'Initialize with' property of the 'Create Formation' operator and in the
    'Update to' property of the 'Update Formation' operator.
    """
    return [
        ("EMPTY", "Empty", "", 1),
        ("ALL_DRONES", "Current positions of drones", "", 2),
        ("SELECTED_OBJECTS", "Selected objects", "", 3),
        ("SELECTED_VERTICES", "Selected vertices", "", 4),
    ]


def collect_points_for_formation_update(selection):
    """Collects the points that should be placed in a formation, given the
    user's selection for the 'Initialize with' or 'Update to' property of the
    corresponding operator.
    """
    if selection == "EMPTY":
        objs_and_points = {}
    elif selection == "ALL_DRONES":
        objs_and_points = {obj: [Vector()] for obj in Collections.find_drones().objects}
    elif selection == "SELECTED_OBJECTS":
        objs_and_points = {obj: [Vector()] for obj in get_selected_objects()}
    elif selection == "SELECTED_VERTICES":
        objs_and_points = {
            obj: [point.co for point in points]
            for obj, points in get_selected_vertices_grouped_by_objects().items()
        }

    points = []
    for obj, points_of_obj in objs_and_points.items():
        local_to_world = obj.matrix_world
        points.extend(local_to_world @ point for point in points_of_obj)

    return points


class UpdateFormationOperator(FormationOperator):
    """Blender operator that removes the selected formation."""

    bl_idname = "skybrush.update_formation"
    bl_label = "Update Selected Formation"
    bl_description = "Update the selected formation from the current selection or from the current positions of the drones"

    update_with = EnumProperty(
        name="Update with",
        items=get_options_for_formation_update(),
        default="ALL_DRONES",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute_on_formation(self, formation, context):
        markers = get_all_markers_from_formation(formation)

        # TODO(ntamas): it would be nicer not to change the selection
        select_only(markers)
        bpy.ops.object.delete()

        points = collect_points_for_formation_update(self.update_with)
        add_markers_to_formation(formation, points)

        return {"FINISHED"}
