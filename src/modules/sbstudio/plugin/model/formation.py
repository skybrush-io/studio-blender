import bpy

from bpy.types import Collection, MeshVertex, Object
from functools import partial
from mathutils import Vector
from numpy import array, c_, dot, ones, zeros
from typing import Iterable, List, Optional, Tuple, Union

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.objects import get_vertices_of_object_in_vertex_group_by_name
from sbstudio.plugin.utils import create_object_in_collection
from sbstudio.plugin.utils.evaluator import get_position_of_object

__all__ = (
    "add_objects_to_formation",
    "add_points_to_formation",
    "count_markers_in_formation",
    "create_formation",
    "create_marker",
    "get_markers_from_formation",
    "get_markers_and_related_objects_from_formation",
    "get_world_coordinates_of_markers_from_formation",
    "is_formation",
)


def create_formation(
    name: str, points: Optional[Iterable[Vector]] = None
) -> Collection:
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

    add_points_to_formation(formation, points, name=name)

    return formation


def create_marker(
    location,
    name: str,
    *,
    type: str = "PLAIN_AXES",
    size: float = 1,
    collection: Optional[Collection] = None,
) -> Object:
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


def add_objects_to_formation(
    formation,
    objects: Optional[Iterable[Object]],
) -> None:
    """Adds the given objects to a formation object as children as-is, _without_
    creating new markers for their current positions.

    Parameters:
        formation: the formation to add the objects to
        objects: the objects to add to the formation
    """
    for obj in objects:
        formation.objects.link(obj)


def add_points_to_formation(
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
    for index, point in enumerate(points or [], start_from):
        marker_name = f"{name} / {index}"
        create_marker(location=point, name=marker_name, collection=formation, size=0.5)


def count_markers_in_formation(formation: Collection) -> int:
    """Returns the number of markers in the given formation.

    Each mesh in the formation counts as one marker, _except_ if the mesh has
    a vertex group whose name matches the corresponding property of the
    object; in that case, all the vertices in the mesh are treated as markers.
    """
    result = 0

    for obj in formation.objects:
        if obj.skybrush.formation_vertex_group:
            result += len(
                get_vertices_of_object_in_vertex_group_by_name(
                    obj, obj.skybrush.formation_vertex_group
                )
            )
        else:
            result += 1

    return result


def get_markers_and_related_objects_from_formation(
    formation: Collection,
) -> List[Tuple[Union[Object, MeshVertex], Object]]:
    """Returns a list containing all the markers and their corresponding
    objects in the formation.

    If a marker is a mesh vertex, returns the mesh vertex and the object
    containing the mesh vertex in a tuple. Otherwise simply returns the
    marker twice in a tuple.

    The order in which the markers are returned from this function are
    consistent with the order in which their positions are returned from
    `get_world_coordinates_of_markers_from_formation()`.
    """
    result = []

    for obj in formation.objects:
        if obj.skybrush.formation_vertex_group:
            result.extend(
                (vertex, obj)
                for vertex in get_vertices_of_object_in_vertex_group_by_name(
                    obj, obj.skybrush.formation_vertex_group
                )
            )
        else:
            result.append((obj, obj))

    return result


def get_markers_from_formation(
    formation: Collection,
) -> List[Union[Object, MeshVertex]]:
    """Returns a list containing all the markers in the formation.

    This function returns all the meshes that are direct children of the
    formation container. Meshes that have a designated vertex group are replaced
    with the vertices in the vertex group.

    The order in which the markers are returned from this function are
    consistent with the order in which their positions are returned from
    `get_world_coordinates_of_markers_from_formation()`.
    """
    result = []

    for obj in formation.objects:
        if obj.skybrush.formation_vertex_group:
            result.extend(
                get_vertices_of_object_in_vertex_group_by_name(
                    obj, obj.skybrush.formation_vertex_group
                )
            )
        else:
            result.append(obj)

    return result


def get_world_coordinates_of_markers_from_formation(
    formation: Collection, *, frame: Optional[int] = None
):
    """Returns a list containing the world coordinates of the markers in the
    formation, as a NumPy array, one marker per row.

    The order in which the markers are returned from this function are
    consistent with the order in which they are returned from
    `get_markers_from_formation()`.

    Parameters:
        formation: the formation to evaluate
        frame: when not `None`, the index of the frame to evaluate the
            coordinates in
    """
    if frame is not None:
        scene = bpy.context.scene
        current_frame = scene.frame_current
        scene.frame_set(frame)
        try:
            return get_world_coordinates_of_markers_from_formation(formation)
        finally:
            scene.frame_set(current_frame)

    vertices_by_obj = {}

    result = []
    num_rows = 0

    for obj in formation.objects:
        if obj.skybrush.formation_vertex_group:
            vertices = get_vertices_of_object_in_vertex_group_by_name(
                obj, obj.skybrush.formation_vertex_group
            )
            vertices_by_obj[obj] = vertices
            num_rows += len(vertices)
        else:
            num_rows += 1

    result = zeros((num_rows, 3))
    row_index = 0

    for obj in formation.objects:
        vertices = vertices_by_obj.get(obj)
        if vertices is not None:
            num_vertices = len(vertices)
            mw = array(obj.matrix_world)
            if num_vertices:
                coords = c_[array([v.co for v in vertices]), ones(num_vertices)]
                result[row_index : (row_index + num_vertices), :] = dot(mw, coords.T)[
                    0:3
                ].T
            row_index += num_vertices
        else:
            result[row_index, :] = get_position_of_object(obj)
            row_index += 1

    return result


def is_formation(object) -> bool:
    """Returns whether the given Blender object is a formation object."""
    if not isinstance(object, Collection):
        return False

    # We cannot move upwards in the Blender collection hierarchy so we proceed
    # downwards instead
    formations = Collections.find_formations(create=False)
    return formations and object in formations.children.values()
