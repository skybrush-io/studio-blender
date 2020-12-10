import bpy

from functools import partial
from mathutils import Vector
from typing import Iterable, Optional

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.utils import create_object_in_collection

__all__ = ("create_formation", "create_marker")


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

    for index, point in enumerate(points, 1):
        marker_name = f"{name} / {index}"
        create_marker(location=point, name=marker_name, collection=formation, size=0.5)

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
