import bpy

from bpy.types import Collection, Context, Mesh, MeshVertex, Object, Scene, VertexGroup
from mathutils import Vector
from typing import Any, Iterable, Optional, Union, cast

from sbstudio.model.types import Coordinate3D

from .utils import with_context, with_scene

__all__ = (
    "create_object",
    "duplicate_object",
    "get_axis_aligned_bounding_box_of_object",
    "get_derived_object_after_applying_modifiers",
    "get_vertices_of_object",
    "get_vertices_of_object_in_vertex_group",
    "get_vertices_of_object_in_vertex_group_by_name",
    "link_object_to_scene",
    "object_contains_vertex",
    "remove_objects",
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
) -> list[MeshVertex]:
    """Returns all the vertices in the given object that are members of the
    given vertex group.

    Parameters:
        object: the object to query
        name: the name of the vertex group
    """
    result: list[MeshVertex] = []
    mesh = object.data if object else None
    if mesh is not None:
        mesh = cast(Mesh, mesh)
        index = group.index
        for vertex in mesh.vertices:
            if any(g.group == index for g in vertex.groups):
                result.append(vertex)
    return result


def get_vertices_of_object_in_vertex_group_by_name(
    object: Object, name: str
) -> list[MeshVertex]:
    """Returns all the vertices in the given object that are members of the
    given vertex group by name.

    Parameters:
        object: the object to query
        name: the name of the vertex group
    """
    group = object.vertex_groups.get(name)
    return get_vertices_of_object_in_vertex_group(object, group) if group else []


@with_scene
def link_object_to_scene(
    object: Object, *, scene: Optional[Scene] = None, allow_nested: bool = False
) -> Object:
    """Links a Blender object to the master collection of the given scene.

    Parameters:
        object: the Blender object to link to the scene
        scene: the Blender scene to link the object to; `None` means to
            use the current scene
        allow_nested: whether the Blender object is allowed to be linked to
            some sub-collection of the scene. When this property is ``True``
            and the object is already part of the scene indirectly via some
            collection, it will not be linked to the scene directly.

    Returns:
        the Blender object
    """
    assert scene is not None
    parent = scene.collection
    is_collection = isinstance(object, bpy.types.Collection)
    parent = parent.children if is_collection else parent.objects

    if allow_nested:
        # Nested membership is allowed so we simply check whether the scene
        # already uses the object indirectly
        num_refs = scene.user_of_id(object)
        if object is scene.skybrush.settings.drone_collection:
            # This reference does not count
            num_refs -= 1
        should_link = num_refs < 1
    else:
        # We need to check whether the scene references the object directly
        should_link = object not in parent.values()

    if should_link:
        parent.link(object)

    return object


def object_contains_vertex(obj: Object, vertex: MeshVertex) -> bool:
    """Returns whether the given object contains the given mesh vertex."""
    mesh = obj.data if obj else None
    index = vertex.index
    return mesh and len(mesh.vertices) > index and mesh.vertices[index] == vertex


def remove_objects(objects: Union[Iterable[Object], Collection]) -> None:
    """Removes the given objects from the current scene. Also supports removing
    an entire collection.
    """
    collection: Optional[Collection] = None
    to_remove: Iterable[Object]

    if isinstance(objects, Collection):
        collection = objects
        to_remove = collection.objects
    else:
        to_remove = objects

    for obj in to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)

    if collection:
        bpy.data.collections.remove(collection)

    """
    # Prevent a circular import with lazy imports
    from .selection import select_only

    # TODO(ntamas): it would be nicer not to change the selection
    select_only(objects, context=context)
    for obj in objects:
        obj.hide_set(False)

    result = bpy.ops.object.delete()
    if result != {"FINISHED"}:
        raise RuntimeError(f"Blender operator returned {result!r}, expected FINISHED")
    """


@with_context
def get_derived_object_after_applying_modifiers(
    obj: Object, *, context: Optional[Context] = None
) -> Object:
    """Returns the object derived from the given base object after applying all
    the mesh modifiers that were set up on it.

    When there is at least one modifier on the base object, returns a temporary
    object that is evaluated from the current dependency graph. When there are
    no modifiers, the function returns the base object itself. Callers should
    assume that they _may_ get a temporary object and are obliged to make a copy
    of any mesh data of the object that they want to hold on to.
    """
    if obj.modifiers:
        assert context is not None
        dependency_graph = context.evaluated_depsgraph_get()
        return obj.evaluated_get(dependency_graph)
    else:
        return obj


@with_context
def get_axis_aligned_bounding_box_of_object(
    obj: Object, *, apply_modifiers: bool = True, context: Optional[Context] = None
) -> tuple[Coordinate3D, Coordinate3D]:
    """Returns the axis-aligned bounding box of the object, in world coordinates.

    Parameters:
        obj: the objet to evaluate
        apply_modifiers: whether the modifiers of the base object should be
            considered when calculating the bounding box
    """
    if apply_modifiers:
        obj = get_derived_object_after_applying_modifiers(obj, context=context)

    mat = obj.matrix_world
    world_coords = [mat @ Vector(coord) for coord in obj.bound_box]

    mins, maxs = list(world_coords[0]), list(world_coords[0])
    for coord in world_coords:
        mins[0] = min(mins[0], coord.x)
        mins[1] = min(mins[1], coord.y)
        mins[2] = min(mins[2], coord.z)
        maxs[0] = max(maxs[0], coord.x)
        maxs[1] = max(maxs[1], coord.y)
        maxs[2] = max(maxs[2], coord.z)

    return tuple(mins), tuple(maxs)
