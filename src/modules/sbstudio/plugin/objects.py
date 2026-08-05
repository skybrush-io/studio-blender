from collections.abc import Iterable
from typing import Any, cast

import bpy
from bpy.types import Collection, Context, Mesh, MeshVertex, Object, Scene, VertexGroup
from mathutils import Vector

from sbstudio.model.types import Coordinate3D

from .utils import with_context, with_scene

__all__ = (
    "create_object",
    "duplicate_object",
    "ensure_direct_scene_child",
    "get_axis_aligned_bounding_box_of_object",
    "get_derived_object_after_applying_modifiers",
    "get_vertices_of_object",
    "get_vertices_of_object_in_vertex_group",
    "get_vertices_of_object_in_vertex_group_by_name",
    "link_to_scene",
    "object_contains_vertex",
    "order_child_collections",
    "remove_objects",
)


@with_scene
def create_object(name: str, data: Any = None, scene: Scene | None = None) -> Object:
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
    link_to_scene(object, scene=scene)
    return object


@with_scene
def duplicate_object(
    object: Object, *, name: str | None = None, scene: Scene | None = None
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
    if name is not None:
        duplicate.name = name
    link_to_scene(duplicate, scene=scene)
    return duplicate


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


def _is_in_scene_collection_tree(collection: Collection, scene: Scene) -> bool:
    """Returns whether ``collection`` appears anywhere under the scene's
    master collection (including nested children).
    """

    def walk(coll: Collection) -> bool:
        if coll == collection:
            return True
        return any(walk(child) for child in coll.children)

    return walk(scene.collection)


def ensure_direct_scene_child(
    collection: Collection, *, scene: Scene | None = None
) -> None:
    """Ensure ``collection`` is a direct child of the scene master collection.

    Unlinks it from any nested parents first. Unlike ``link_to_scene(...,
    allow_nested=True)``, this actively promotes nested collections to the
    scene root.
    """
    if scene is None:
        scene = bpy.context.scene
    assert scene is not None

    root = scene.collection

    for parent in list(bpy.data.collections):
        if collection in parent.children.values():
            parent.children.unlink(collection)

    for other_scene in bpy.data.scenes:
        if collection in other_scene.collection.children.values():
            other_scene.collection.children.unlink(collection)

    root.children.link(collection)


def order_child_collections(
    parent: Collection, ordered: Iterable[Collection]
) -> None:
    """Reorder ``parent``'s child collections so ``ordered`` appear in that
    relative sequence.

    Other children keep their relative order. The block of ordered collections
    is placed starting at the earliest current index among them.
    """
    children = parent.children
    current = list(children)
    present = [coll for coll in ordered if coll in children.values()]
    if len(present) < 2:
        return

    insert_at = min(current.index(coll) for coll in present)
    remaining = [coll for coll in current if coll not in present]
    insert_at = min(insert_at, len(remaining))
    desired = remaining[:insert_at] + present + remaining[insert_at:]

    for target_index, coll in enumerate(desired):
        current_index = list(children).index(coll)
        if current_index != target_index:
            children.move(current_index, target_index)


@with_scene
def link_to_scene(
    object: Object | Collection,
    *,
    scene: Scene | None = None,
    allow_nested: bool = False,
) -> None:
    """Links a Blender object or collection to the master collection of the given scene.

    Parameters:
        object: the Blender object or collection to link to the scene
        scene: the Blender scene to link the object to; `None` means to
            use the current scene
        allow_nested: whether the Blender object is allowed to be linked to
            some sub-collection of the scene. When this property is ``True``
            and the object is already part of the scene indirectly via some
            collection, it will not be linked to the scene directly.
    """
    assert scene is not None

    parent = scene.collection
    is_collection = isinstance(object, Collection)
    parent = parent.children if is_collection else parent.objects

    if allow_nested:
        # Prefer an explicit collection-tree walk over scene.user_of_id().
        # PointerProperties such as settings.drone_collection inflate
        # user_of_id even when the collection is not in the scene hierarchy,
        # which previously prevented re-linking and made newly created drones
        # unselectable ("not in View Layer").
        if is_collection:
            should_link = not _is_in_scene_collection_tree(object, scene)
        else:
            should_link = not any(
                _is_in_scene_collection_tree(coll, scene)
                for coll in object.users_collection
            )
    else:
        # We need to check whether the scene references the object directly
        should_link = object not in parent.values()

    if should_link:
        parent.link(cast(Any, object))


def object_contains_vertex(obj: Object, vertex: MeshVertex) -> bool:
    """Returns whether the given object contains the given mesh vertex."""
    mesh = obj.data if obj else None
    index = vertex.index
    return mesh and len(mesh.vertices) > index and mesh.vertices[index] == vertex


def remove_objects(objects: Iterable[Object] | Collection) -> None:
    """Removes the given objects from the current scene. Also supports removing
    an entire collection.
    """
    collection: Collection | None = None
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
    obj: Object, *, context: Context | None = None
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
    obj: Object, *, apply_modifiers: bool = True, context: Context | None = None
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
