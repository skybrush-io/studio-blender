"""Utility functions directly related to the Blender API."""

import bpy

from contextlib import contextmanager
from operator import attrgetter

from .collections import (
    create_object_in_collection,
    ensure_object_exists_in_collection,
    find_empty_slot_in,
    get_object_in_collection,
)
from .debounce import debounced
from .decorators import with_context, with_scene, with_screen
from .identifiers import create_internal_id, propose_name, propose_names
from .platform import get_temporary_directory, open_file_with_default_application

__all__ = (
    "create_object_in_collection",
    "create_internal_id",
    "debounced",
    "descendants_of",
    "ensure_object_exists_in_collection",
    "find_empty_slot_in",
    "get_object_in_collection",
    "get_temporary_directory",
    "overridden_context",
    "open_file_with_default_application",
    "propose_name",
    "propose_names",
    "remove_if_unused",
    "with_context",
    "with_scene",
    "with_screen",
)


def descendants_of(objects, selector="children"):
    """Iteratees over all descendants of the given objects, recursively,
    including the seed objects as well.

    Parameters:
        objects: the objects whose descendants are to be selected
        selector: a callable that takes an object and returns an iterable that
            iterates over all its children, or the name of a property that
            must exist on the object.
    """
    if isinstance(selector, str):
        selector = attrgetter(selector)

    if not callable(selector):
        raise TypeError("selector must be string or callable")

    if hasattr(objects, "__iter__"):
        queue = list(objects)
    else:
        queue = [objects]

    seen = set()
    while queue:
        obj = queue.pop()
        if obj in seen:
            continue

        seen.add(obj)
        yield obj

        queue.extend(selector(obj))


@contextmanager
def overridden_context(current_context=None, **kwds):
    """Context manager that overrides parts of the current Blender context and
    returns a new context object with the overridden parameters.

    The parts of the context to override must be specified with keyword
    arguments (e.g., `with overridden_context(area=foo):`).

    Parameters:
        current_context (Optional[bpy.Context]): the current Blender context.
            `None` means to use `bpy.context`

    Returns:
        bpy.Context: a new Blender context with the overridden parts
    """
    result = (current_context or bpy.context).copy()
    for key, value in kwds.items():
        setattr(result, key, value)
    yield result


def remove_if_unused(obj, from_) -> bool:
    """Removes a Blender object from its containing collection if the object
    has only one user (presumably ourselves).

    Parameters:
        obj: the Blender object to remove
        from_: the Blender collection to remove the object from

    Returns:
        whether the object was removed from its collection
    """
    if obj and not obj.use_fake_user and obj.users == 1:
        from_.remove(obj, do_unlink=True)
        return True
    else:
        return False
