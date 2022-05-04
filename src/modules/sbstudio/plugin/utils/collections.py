"""Utility functions directly related to the Blender API."""

import bpy

from bpy.types import Collection, Object

from inspect import signature
from itertools import count
from typing import Any, Callable, Optional, Tuple

from sbstudio.utils import get_moves_required_to_sort_collection

from .identifiers import create_internal_id

__all__ = (
    "create_object_in_collection",
    "find_empty_slot_in",
    "get_object_in_collection",
    "sort_collection",
)


def create_object_in_collection(
    collection: Collection,
    name: str,
    factory: Optional[Callable[[], Any]] = None,
    remover: Optional[Callable[[Object], None]] = None,
    internal: bool = False,
    *args,
    **kwds,
):
    """Creates a new Blender object in the given collection with the given
    name. Removes any previous objects in the collection that exist with
    the given name.

    Parameters:
        collection: a Blender collection with `find()`, `new()` and `remove()`
            methods and numeric indexing support.
        name: the identifier of the object to retrieve. When `internal` is set
            to `True`, it will be passed through `create_internal_id()` to
            ensure that the names we use do not conflict with other public
            names created by the user in the collection.
        factory: a factory function to create the new object. When it is
            specified, the object will be created by calling the factory
            function with no arguments, and it will be linked to the
            collection by calling `link()` on the collection. When it is
            not specified, the `new()` or `load()` method of the collection will
            be used instead.
        remover: optional remover function that is called with the existing
            item and optionally the collection if an item with the given name
            already exists
        internal: whether the object is an internal, Skybrush-specific object
            that should be marked explicitly
    """
    existing = get_object_in_collection(
        collection, name, default=None, internal=internal
    )
    if existing is not None:
        if callable(remover):
            sig = signature(remover)
            if len(sig.parameters) > 1:
                remover(existing, collection)
            else:
                remover(existing)
        elif hasattr(collection, "remove"):
            collection.remove(existing)
        elif hasattr(collection, "unlink"):
            collection.unlink(existing)
            if not existing.use_fake_user and existing.users == 0:
                if isinstance(existing, Collection):
                    bpy.data.collections.remove(existing)
                elif isinstance(existing, Object):
                    bpy.data.objects.remove(existing)

    if internal:
        name = create_internal_id(name)

    if factory is not None:
        object = factory()
        object.name = name
        collection.link(object)
    elif hasattr(collection, "new"):
        object = collection.new(name, *args, **kwds)
    else:
        object = collection.load(*args, **kwds)
        object.name = name

    return object


def ensure_object_exists_in_collection(
    collection: Collection,
    name: str,
    factory: Optional[Callable[[], Any]] = None,
    internal: bool = False,
    *args,
    **kwds,
) -> Tuple[Any, bool]:
    """Ensures that a Blender object with the given name exists in the given
    collection.

    Parameters:
        collection: a Blender collection with `find()`, `new()` and `remove()`
            methods and numeric indexing support.
        name: the identifier of the object to retrieve. When `internal` is set
            to `True`, it will be passed through `create_internal_id()` to
            ensure that the names we use do not conflict with other public
            names created by the user in the collection.
        factory: a factory function to create the new object. When it is
            specified, the object will be created by calling the factory
            function with no arguments, and it will be linked to the
            collection by calling `objects.link()` on the collection. When it is
            not specified, the `new()` or `load()` method of the collection will
            be used instead.
        internal: whether the object is an internal, Skybrush-specific object
            that should be marked explicitly

    Returns:
        a tuple containing the existing object in the collection or a newly
        created one if no object with the given name existed in the collection
        before, and a boolean that encodes whether this is a newly created
        object or not
    """
    existing = get_object_in_collection(
        collection, name, default=None, internal=internal
    )
    if existing is not None:
        return existing, False
    else:
        return (
            create_object_in_collection(
                collection, name, factory, internal=internal, *args, **kwds
            ),
            True,
        )


def find_empty_slot_in(collection: Collection, start_from: int = 0):
    """Finds the first empty slot in the given indexable Blender collection.

    Parameters:
        collection: the Blender collection
        start_from: the index to start the search from

    Returns:
        int: the index of the first empty slot in the collection
    """
    for index in count(start_from):
        if collection[index] is None:
            return index


def get_object_in_collection(
    collection: Collection, name: str, internal: bool = False, **kwds
):
    """Returns a Blender object from a given Blender collection with the
    given name.

    Parameters:
        collection: a Blender collection with `find()` and numeric indexing
            support.
        name: the identifier of the object to retrieve. When `internal` is set
            to `True`, it will be passed through `create_internal_id()` to
            ensure that the names we use do not conflict with other public
            names created by the user in the collection.
        internal: whether the object is an internal, Skybrush-specific object
            that should be marked explicitly

    Keyword arguments:
        default: when specified and the object does not exist, returns this
            default object instead

    Returns:
        object: the Blender object from the collection with the given name,
            or the default object if the Blender object does not exist but
            a default was provided

    Throws:
        KeyError: if the Blender object does not exist in the collection and
            no default was provided
    """
    our_id = create_internal_id(name) if internal else name

    index = collection.find(our_id)
    if index >= 0:
        return collection[index]
    elif "default" in kwds:
        return kwds["default"]
    else:
        raise KeyError("No such object in collection: {0!r}".format(name))


def sort_collection(collection: Collection, key: Callable[[Any], int]) -> None:
    """Sorts the given Blender collection using the given sorting key, with
    the limited set of reordering methods provided by Blender.

    The collection needs to have a method named ``move()`` that takes two
    indices and moves the item at the source index to the given target index.
    """
    moves = get_moves_required_to_sort_collection(collection, key)
    for source, target in moves:
        collection.move(source, target)
