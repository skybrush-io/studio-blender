import bpy

from bpy.props import EnumProperty
from mathutils import Vector

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.formation import (
    add_objects_to_formation,
    add_points_to_formation,
    get_all_markers_from_formation,
)
from sbstudio.plugin.selection import (
    get_selected_objects,
    get_selected_vertices_grouped_by_objects,
    has_selection,
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
        (
            "POSITIONS_OF_SELECTED_OBJECTS",
            "Current positions of selected objects",
            "",
            4,
        ),
        (
            "POSITIONS_OF_SELECTED_VERTICES",
            "Current positions of selected vertices",
            "",
            5,
        ),
    ]


def propose_mode_for_formation_update(context) -> str:
    """Proposes a sensible value for the 'Initialize with' property of the
    'Create Formation' operator and the 'Update to' property of the
    'Update Formation' operator, given the current Blender context.

    Returns:
        the proposed value or `None` if the previous setting should be used
    """
    if context.mode == "EDIT_MESH":
        # We are in Edit mode.
        # TODO(ntamas): use "SELECTED_VERTICES" once we have implemented
        # using vertex groups in a formation
        return (
            "POSITIONS_OF_SELECTED_VERTICES"
            if has_selection(context=context)
            else "EMPTY"
        )
    else:
        # We are not in Edit mode (most likely Object mode)
        return "SELECTED_OBJECTS" if has_selection(context=context) else "ALL_DRONES"


def collect_objects_and_points_for_formation_update(selection):
    """Collects the objects and points that should be placed in a formation,
    given the user's selection for the 'Initialize with' or 'Update to' property
    of the corresponding operator.

    The returned objects will be added to the formation "as is". For each
    returned _point_, an empty mesh will be created and it will be added to the
    formation instead of the point.
    """
    objects = []

    if selection == "EMPTY":
        points_in_local_coords = {}
    elif selection == "ALL_DRONES":
        points_in_local_coords = {
            obj: [Vector()] for obj in Collections.find_drones().objects
        }
    elif selection == "SELECTED_OBJECTS":
        objects.extend(get_selected_objects())
        points_in_local_coords = {}
    elif selection == "POSITIONS_OF_SELECTED_OBJECTS":
        points_in_local_coords = {obj: [Vector()] for obj in get_selected_objects()}
    elif selection == "POSITIONS_OF_SELECTED_VERTICES":
        points_in_local_coords = {
            obj: [point.co for point in points]
            for obj, points in get_selected_vertices_grouped_by_objects().items()
        }

    points = []
    for parent, points_of_parent in points_in_local_coords.items():
        local_to_world = parent.matrix_world
        points.extend(local_to_world @ point for point in points_of_parent)

    return objects, points


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
        self.update_with = propose_mode_for_formation_update(context)
        return context.window_manager.invoke_props_dialog(self)

    def execute_on_formation(self, formation, context):
        markers = get_all_markers_from_formation(formation)

        objects, points = collect_objects_and_points_for_formation_update(
            self.update_with
        )

        # Make sure to delete only those objects where the only user was the
        # formation; if there were any other users, do not delete the object as
        # the user might need it for something. Also do not delete objects that
        # would be re-added to the formation.
        to_unlink = set(marker for marker in markers if marker.users > 1)
        to_delete = set(markers) - to_unlink - set(objects)

        # Unlink the markers from the formation that are used elsewhere
        for marker in to_unlink:
            formation.objects.unlink(marker)

        # Delete the markers from the formation that are not used elsewhere
        # TODO(ntamas): it would be nicer not to change the selection
        select_only(to_delete)
        bpy.ops.object.delete()

        add_points_to_formation(formation, points)
        add_objects_to_formation(formation, objects)

        return {"FINISHED"}
