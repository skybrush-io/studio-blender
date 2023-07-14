from bpy.props import EnumProperty
from bpy.types import Context, Scene
from mathutils import Vector

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.formation import (
    add_objects_to_formation,
    add_points_to_formation,
)
from sbstudio.plugin.objects import remove_objects
from sbstudio.plugin.selection import (
    get_selected_objects,
    get_selected_vertices_grouped_by_objects,
    has_selection,
)

from .base import FormationOperator

__all__ = ("UpdateFormationOperator",)


#: Formation update options, kept here in dictionary to ensure that Python has
#: a reference to their strings all the time -- there is a bug in Blender that
#: would cause it to crash if we do not have a reference
FORMATION_UPDATE_ITEMS = {
    "EMPTY": ("EMPTY", "Empty", "", 1),
    "ALL_DRONES": ("ALL_DRONES", "Current positions of drones", "", 2),
    "SELECTED_OBJECTS": ("SELECTED_OBJECTS", "Selected objects", "", 3),
    "POSITIONS_OF_SELECTED_OBJECTS": (
        "POSITIONS_OF_SELECTED_OBJECTS",
        "Current positions of selected objects",
        "",
        4,
    ),
    "POSITIONS_OF_SELECTED_VERTICES": (
        "POSITIONS_OF_SELECTED_VERTICES",
        "Current positions of selected vertices",
        "",
        5,
    ),
}


def get_options_for_formation_update(scene: Scene, context: Context):
    """Returns a list containing the options that we support in the
    'Initialize with' property of the 'Create Formation' operator and in the
    'Update to' property of the 'Update Formation' operator.
    """
    global FORMATION_UPDATE_ITEMS

    items = ["EMPTY", "ALL_DRONES"]

    if context and context.mode == "EDIT_MESH":
        items.extend(["POSITIONS_OF_SELECTED_VERTICES"])
    else:
        items.extend(["SELECTED_OBJECTS", "POSITIONS_OF_SELECTED_OBJECTS"])

    return [FORMATION_UPDATE_ITEMS[item] for item in items]


def propose_mode_for_formation_update(context) -> str:
    """Proposes a sensible value for the 'Initialize with' property of the
    'Create Formation' operator and the 'Update to' property of the
    'Update Formation' operator, given the current Blender context.

    Returns:
        the proposed value or `None` if the previous setting should be used
    """
    if context and context.mode == "EDIT_MESH":
        # We are in Edit mode
        return (
            "POSITIONS_OF_SELECTED_VERTICES"
            if has_selection(context=context)
            else "EMPTY"
        )
    else:
        # We are not in Edit mode (most likely Object mode)
        return "SELECTED_OBJECTS" if has_selection(context=context) else "EMPTY"


def collect_objects_and_points_for_formation_update(selection, name):
    """Collects the objects and points that should be placed in a formation,
    given the user's selection for the 'Initialize with' or 'Update to' property
    of the corresponding operator.

    The returned objects will be added to the formation "as is". For each
    returned _point_, an empty mesh will be created and it will be added to the
    formation instead of the point.

    Args:
        selection: the selection from `FORMATION_UPDATE_ITEMS`
        name: the name of the formation

    Returns:
        objects and points to be used for updating the given formation

    """
    objects = []
    points_in_local_coords = {}

    if selection == "EMPTY":
        pass
    elif selection == "ALL_DRONES":
        points_in_local_coords = {
            obj: [Vector()] for obj in Collections.find_drones().objects
        }
    elif selection == "SELECTED_OBJECTS":
        objects.extend(get_selected_objects())
    elif selection == "POSITIONS_OF_SELECTED_OBJECTS":
        points_in_local_coords = {obj: [Vector()] for obj in get_selected_objects()}
    elif selection == "POSITIONS_OF_SELECTED_VERTICES":
        points_in_local_coords = {
            obj: [point.co for point in points]
            for obj, points in get_selected_vertices_grouped_by_objects().items()
        }
    else:
        raise ValueError("Unknown selection: {}".format(selection))

    points = []
    for parent, points_of_parent in points_in_local_coords.items():
        local_to_world = parent.matrix_world
        points.extend(local_to_world @ point for point in points_of_parent)

    return objects, points


class UpdateFormationOperator(FormationOperator):
    """Blender operator that updates the markers in the selected formation."""

    bl_idname = "skybrush.update_formation"
    bl_label = "Update Selected Formation"
    bl_description = "Update the selected formation from the current selection or from the current positions of the drones"

    update_with = EnumProperty(
        name="Update with",
        items=get_options_for_formation_update,
    )

    def invoke(self, context, event):
        self.update_with = propose_mode_for_formation_update(context)
        return context.window_manager.invoke_props_dialog(self)

    def execute_on_formation(self, formation, context):
        objects_in_formation = formation.objects

        new_objects, new_points = collect_objects_and_points_for_formation_update(
            self.update_with, formation.name
        )

        # Make sure to delete only those objects where the only user was the
        # formation; if there were any other users, do not delete the object as
        # the user might need it for something. Also do not delete objects that
        # would be re-added to the formation.
        to_unlink = {obj for obj in objects_in_formation if obj.users > 1}
        to_delete = set(objects_in_formation) - to_unlink - set(new_objects)

        # Unlink the markers from the formation that are used elsewhere
        for obj in to_unlink:
            formation.objects.unlink(obj)

        # Delete the markers from the formation that are not used elsewhere
        remove_objects(to_delete)

        # Add the new points and objects to the formation
        add_points_to_formation(formation, new_points)
        add_objects_to_formation(formation, new_objects)

        return {"FINISHED"}
