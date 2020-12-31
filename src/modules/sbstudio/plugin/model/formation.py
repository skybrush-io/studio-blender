import bpy

from bpy.types import Collection
from functools import partial
from mathutils import Vector
from typing import Iterable, Optional

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.utils import create_object_in_collection

__all__ = (
    "add_markers_to_formation",
    "create_formation",
    "create_marker",
    "get_all_markers_from_formation",
    "is_formation",
)


def create_formation(name: str, points: Optional[Iterable[Vector]] = None):
    """Creates a new static formation object with the given name and the given
    points.

    Parameters:
        name: the name of the formation
        points: iterable yielding the points in the formation, or `None` if the
            formation should be empty

    Returns:
        the formation object that was created
    """
    formation = create_object_in_collection(
        Collections.find_formations().children,
        name,
        factory=partial(bpy.data.collections.new, name),
    )

    add_markers_to_formation(formation, points, name=name)

    return formation


def create_marker(
    location, name: str, *, type: str = "PLAIN_AXES", size: float = 1, collection=None
):
    """Creates a new point marker (typically part of a formation) at the
    given location.

    Parameters:
        location: the location where the new marker should be created
        name: the name of the marker
        type: the Blender type (shape) of the marker
        size: the size of the marker in the Blender viewport
        collection: the collection that the new marker should be a part of;
            use `None` to add it to the scene collection
    """
    collection = collection or bpy.context.scene.scene_collection

    marker = bpy.data.objects.new(name, None)
    marker.empty_display_size = size
    marker.empty_display_type = type
    marker.location = location

    collection.objects.link(marker)

    return marker


def add_markers_to_formation(
    formation,
    points: Optional[Iterable[Vector]],
    *,
    name: Optional[str] = None,
    start_from: int = 1,
) -> None:
    """Creates new markers in a formation object.

    Parameters:
        formation: the formation to create the markers in
        points: the points to add to the formation
        name: the name of the formation
        start_from: the index of the first point to add; used when naming the
            newly added markers
    """
    name = name or formation.name
    for index, point in enumerate(points, start_from):
        marker_name = f"{name} / {index}"
        create_marker(location=point, name=marker_name, collection=formation, size=0.5)


def get_all_markers_from_formation(formation) -> list:
    """Returns a list containing all the markers in the formation.

    This function returns only empty meshes from the formation, not any other
    objects that were added by the user.
    """
    return [
        point for point in formation.objects if getattr(point, "type", None) == "EMPTY"
    ]


def is_formation(object) -> bool:
    """Returns whether the given Blender object is a formation object."""
    if not isinstance(object, Collection):
        return False

    # We cannot move upwards in the Blender collection hierarchy so we proceed
    # downwards instead
    formations = Collections.find_formations(create=False)
    return formations and object in formations.children.values()
