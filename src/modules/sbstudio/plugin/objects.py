import bpy

from bpy.types import MeshVertex, Object, Scene, VertexGroup
from typing import Any, List, Optional

from .utils import with_scene

__all__ = (
    "create_object",
    "duplicate_object",
    "link_object_to_scene",
)


@with_scene
def create_object(name: str, data: Any = None, scene: Optional[Scene] = None) -> Object:
    """Creates a new generic Blender object in the given scene.

    Parameters:
        name: the name of the object to create
        data: the data of the Blender object; typically a mesh, but may be
            anything else that Blender allows. `None` creates an empty object.
        scene: the Blender scene to add the object to; `None` means to use
            current scene

    Returns:
        the created object
    """
    object = bpy.data.objects.new(name, data)
    return link_object_to_scene(object, scene=scene)


@with_scene
def duplicate_object(
    object: Object, *, name: Optional[str] = None, scene: Optional[Scene] = None
) -> Object:
    """Duplicates a Blender object under a different name.

    Parameters:
        object: the Blender object to duplicate
        name: the name of the object to create; `None` means not to change
            the name that Blender assigned by default
        scene: the Blender scene to add the object to; `None` means to use
            current scene

    Returns:
        the newly created object
    """
    duplicate = object.copy()
    duplicate.data = object.data.copy()
    duplicate.name = name
    return link_object_to_scene(duplicate, scene=scene)


def get_vertices_of_object(object: Object):
    """Returns all the vertices in the given object, or an empty list if the
    object is not a mesh.
    """
    data = object.data if object else None
    return getattr(data, "vertices", [])


def get_vertices_of_object_in_vertex_group(
    object: Object, group: VertexGroup
) -> List[MeshVertex]:
    """Returns all the vertices in the given object that are members of the
    given vertex group.

    Parameters:
        object: the object to query
        name: the name of the vertex group
    """
    result = []
    mesh = object.data if object else None
    if mesh is not None:
        index = group.index
        for vertex in mesh.vertices:
            if any(g.group == index for g in vertex.groups):
                result.append(vertex)
    return result


def get_vertices_of_object_in_vertex_group_by_name(
    object: Object, name: str
) -> List[MeshVertex]:
    """Returns all the vertices in the given object that are members of the
    given vertex group by name.

    Parameters:
        object: the object to query
        name: the name of the vertex group
    """
    group = object.vertex_groups.get(name)
    return get_vertices_of_object_in_vertex_group(object, group) if group else []


@with_scene
def link_object_to_scene(object: Object, *, scene: Optional[Scene] = None) -> Object:
    """Links a Blender object to the master collection of the given scene.

    Parameters:
        object: the Blender object to link to the scene
        scene: the Blender scene to link the object to; `None` means to
            use the current scene

    Returns:
        the Blender object
    """
    parent = scene.collection

    if isinstance(object, bpy.types.Collection):
        parent = parent.children
    else:
        parent = parent.objects

    if object not in parent.values():
        parent.link(object)

    return object
