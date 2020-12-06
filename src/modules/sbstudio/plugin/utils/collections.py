"""Utility functions directly related to the Blender API."""

from itertools import count
from typing import Any, Callable, Optional

from .identifiers import create_internal_id

__all__ = (
    "create_object_in_collection",
    "find_empty_slot_in",
    "get_object_in_collection",
)


def create_object_in_collection(
    collection,
    name: str,
    factory: Optional[Callable[[], Any]] = None,
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
        internal: whether the object is an internal, Skybrush-specific object
            that should be marked explicitly
    """
    existing = get_object_in_collection(
        collection, name, default=None, internal=internal
    )
    if existing is not None:
        collection.remove(existing)

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
    collection,
    name: str,
    factory: Optional[Callable[[], Any]] = None,
    internal: bool = False,
    *args,
    **kwds,
):
    """Ensures that a Blender object with the given name exists in the given
    collection with the given.

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
        the existing object in the collection or a newly created one if no
        object with the given name existed in the collection before
    """
    existing = get_object_in_collection(
        collection, name, default=None, internal=internal
    )
    if existing is not None:
        return existing
    else:
        return create_object_in_collection(
            collection, name, factory, internal, *args, **kwds
        )


def find_empty_slot_in(collection, start_from=0):
    """Finds the first empty slot in the given indexable Blender collection.

    Parameters:
        collection: the Blender collection
        start_from (int): the index to start the search from

    Returns:
        int: the index of the first empty slot in the collection
    """
    for index in count(start_from):
        if collection[index] is None:
            return index


def get_object_in_collection(collection, name: str, internal: bool = False, **kwds):
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
