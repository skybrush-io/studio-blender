import bpy

from typing import Any, Optional

from .decorators import with_scene

__all__ = (
    "create_object",
    "duplicate_object",
    "link_object_to_scene",
)


@with_scene
def create_object(
    name: str, data: Any = None, scene: Optional[bpy.types.Scene] = None
) -> Any:
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
    object, *, name: Optional[str] = None, scene: Optional[bpy.types.Scene] = None
) -> Any:
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


@with_scene
def link_object_to_scene(object, *, scene: Optional[bpy.types.Scene] = None):
    """Links a Blender object to the master collection of the given scene.

    Parameters:
        object: the Blender object to link to the scene
        scene: the Blender scene to link the object to; `None` means to
            use the current scene

    Returns:
        object: the Blender object
    """
    parent = scene.collection
    if isinstance(object, bpy.types.Collection):
        parent.children.link(object)
    else:
        parent.objects.link(object)
    return object
