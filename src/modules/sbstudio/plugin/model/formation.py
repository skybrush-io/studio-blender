from __future__ import annotations

import bpy

from bpy.types import Collection
from functools import partial
from itertools import count
from mathutils import Vector
from numpy import array, c_, dot, ones, zeros
from typing import Iterable, List, Optional, Sequence, Tuple, Union, TYPE_CHECKING

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.objects import (
    get_derived_object_after_applying_modifiers,
    get_vertices_of_object_in_vertex_group_by_name,
)
from sbstudio.plugin.utils import create_object_in_collection
from sbstudio.plugin.utils.evaluator import get_position_of_object

if TYPE_CHECKING:
    from bpy.types import MeshVertex, Object

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
    "remove_formation",
)


def _get_marker_name(formation: str, index: int) -> str:
    """Proposes a new name for a marker with the given index in the given
    formation.
    """
    return f"{formation} - {index + 1}"


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
        remover=remove_formation,
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
    assert collection is not None

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
) -> List[Object]:
    """Creates new markers in a formation object.

    Parameters:
        formation: the formation to create the markers in
        points: the points to add to the formation
        name: the name of the formation

    Returns:
        the markers that were added
    """
    result = []

    formation_name = name or formation.name or ""
    existing_names = {obj.name for obj in formation.objects}

    index = 0
    for index in count():
        name_candidate = _get_marker_name(formation_name, index)
        if name_candidate not in existing_names:
            break

    for point in points or []:
        while True:
            marker_name = _get_marker_name(formation_name, index)
            if marker_name in existing_names:
                index += 1
            else:
                break

        marker = create_marker(
            location=point, name=marker_name, collection=formation, size=0.5
        )
        result.append(marker)

        existing_names.add(marker_name)
        index += 1

    return result


def count_markers_in_formation(formation: Collection) -> int:
    """Returns the number of markers in the given formation.

    Each mesh in the formation counts as one marker, _except_ if the mesh has
    a vertex group whose name matches the corresponding property of the
    object; in that case, all the vertices in the mesh are treated as markers.

    The mesh is evaluated before applying mesh modifiers.
    """
    result = 0

    for obj in formation.objects:
        vertex_group_name = obj.skybrush.formation_vertex_group
        if vertex_group_name:
            result += len(
                get_vertices_of_object_in_vertex_group_by_name(obj, vertex_group_name)
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

    It is guaranteed that the returned mesh vertices are not _derived_ vertices
    (obtained after applying the modifiers) but the _original_ vertices that are
    actually part of the base mesh.
    """

    # WARNING: When refactoring, do _not_ change the order in which this
    # function returns the markers because that would mess up the stored
    # mappings of the StoryboardEntry_ objects. Doing so would be a breaking
    # change that messes up the mappings in already-saved scenes.

    result = []

    for obj in formation.objects:
        vertex_group_name = obj.skybrush.formation_vertex_group
        if vertex_group_name:
            result.extend(
                (vertex, obj)
                for vertex in get_vertices_of_object_in_vertex_group_by_name(
                    obj, vertex_group_name
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
    `get_world_coordinates_of_markers_from_formation()`. The order is also
    consistent with the order of objects within the formation collection
    according to Blender.

    It is guaranteed that the returned mesh vertices are not _derived_ vertices
    (obtained after applying the modifiers) but the _original_ vertices that are
    actually part of the base mesh.
    """
    result = []

    for obj in formation.objects:
        vertex_group_name = obj.skybrush.formation_vertex_group
        if vertex_group_name:
            result.extend(
                get_vertices_of_object_in_vertex_group_by_name(obj, vertex_group_name)
            )
        else:
            result.append(obj)

    return result


def ensure_formation_consists_of_points(
    formation: Collection, points: Sequence[Vector]
) -> None:
    """Ensures that the given formation consists of only empty meshes placed
    at the given points in world coordinates.

    If the formation contains non-empty meshes, these will be removed. The
    remaining empties will be moved to the given points. If there are more
    points than empties in the formation, new empties will be added as needed.
    """
    # Remove all children
    for child in formation.children:
        formation.children.unlink(child)  # type: ignore

    # Remove all objects that are not empties
    for obj in formation.objects:
        if getattr(obj, "type", None) != "EMPTY":
            if obj.users <= 1:
                bpy.data.objects.remove(obj)
            else:
                formation.objects.unlink(obj)

    # Move the empties to the points
    num_empties = len(formation.objects)
    for obj, point in zip(formation.objects, points):
        obj.location = point  # type: ignore

    # Add any remaining empties if needed
    if num_empties < len(points):
        add_points_to_formation(formation, points[num_empties:])


def get_world_coordinates_of_markers_from_formation(
    formation: Collection, *, frame: Optional[int] = None, apply_modifiers: bool = True
):
    """Returns a list containing the world coordinates of the markers in the
    formation, as a NumPy array, one marker per row.

    The order in which the markers are returned from this function are
    consistent with the order in which they are returned from
    `get_markers_from_formation()`. The order is also consistent with the
    order of objects within the formation collection according to Blender.

    The coordinates are evaluated _after_ applying the mesh modifiers by
    default, unless ``apply_modifiers`` is set to ``False``, in which case they
    are evaluated _before_ applying the mesh modifiers.

    Parameters:
        formation: the formation to evaluate
        frame: when not `None`, the index of the frame to evaluate the
            coordinates in
    """
    # TODO(ntamas): check whether there are any modifiers in the modifier stack
    # that might indicate that the mesh is mutated, in which case we cannot use
    # vertex groups!

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
        vertex_group_name = obj.skybrush.formation_vertex_group
        if vertex_group_name:
            # We need to be careful here. If the mesh has modifiers, we might
            # have to evaluate the vertex group on the _modified_ mesh, not on
            # the base mesh.
            if apply_modifiers:
                derived_object = get_derived_object_after_applying_modifiers(obj)
            else:
                derived_object = obj
            vertices = get_vertices_of_object_in_vertex_group_by_name(
                derived_object, vertex_group_name
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


def remove_formation(formation: Collection) -> None:
    """Removes the given formation and all the markers in it if they are
    unused.
    """
    formations = Collections.find_formations(create=False)
    if not formations:
        return

    formations.children.unlink(formation)

    for obj in formation.objects:
        if obj.users <= 1:
            bpy.data.objects.remove(obj)

    bpy.data.collections.remove(formation)
