"""Utility functions directly related to the Blender API."""

from __future__ import annotations
from operator import attrgetter

import bpy
import re

from bpy.types import Collection, Object

from inspect import signature
from itertools import count
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
    Sequence,
    TypeVar,
    TYPE_CHECKING,
    Union,
    overload,
)

from .identifiers import create_internal_id

if TYPE_CHECKING:
    from bpy.types import bpy_prop_collection, ID

__all__ = (
    "create_object_in_collection",
    "filter_collection",
    "find_empty_slot_in",
    "get_object_in_collection",
    "pick_unique_name",
    "sort_collection",
)

T = TypeVar("T", bound="ID")
D = TypeVar("D")


def create_object_in_collection(
    collection: bpy_prop_collection[T],
    name: str,
    factory: Optional[Callable[[], T]] = None,
    remover: Optional[Callable[[T], None]] = None,
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
                remover(existing, collection)  # type: ignore
            else:
                remover(existing)
        elif hasattr(collection, "remove"):
            collection.remove(existing)  # type: ignore
        elif hasattr(collection, "unlink"):
            collection.unlink(existing)  # type: ignore
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
    collection: bpy_prop_collection[T],
    name: str,
    factory: Optional[Callable[[], T]] = None,
    internal: bool = False,
    *args,
    **kwds,
) -> Tuple[T, bool]:
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
                collection,
                name,
                factory,
                internal=internal,
                *args,  # noqa: B026
                **kwds,
            ),
            True,
        )


def find_empty_slot_in(collection: bpy_prop_collection, start_from: int = 0) -> int:
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

    raise RuntimeError("should never reach this point")


@overload
def get_object_in_collection(
    collection: bpy_prop_collection[T], name: str, internal: bool = False, **kwds
) -> T: ...


@overload
def get_object_in_collection(
    collection: bpy_prop_collection[T], name: str, internal: bool = False, *, default: D
) -> Union[T, D]: ...


def get_object_in_collection(
    collection: bpy_prop_collection[T], name: str, internal: bool = False, **kwds
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
        the Blender object from the collection with the given name,
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


def _get_actions_required_to_sort_collection_with_move_method(
    items: Sequence[Any], key: Optional[Callable[[Any], Any]] = None
) -> List[Tuple[int, int]]:
    """Given a list of items and an optional sorting key function, returns a
    list of from-to pairs representing steps that are needed to sort the list
    with single-item moves. This is useful for sorting Blender collections
    with its `move()` method.
    """
    result = []
    num_items = len(items)

    if num_items:
        if key:
            items = [key(item) for item in items]

        indexes = sorted(range(num_items), key=items.__getitem__)

        for front, index in enumerate(indexes):
            if index != front:
                result.append((index, front))
                for j in range(front + 1, num_items):
                    if indexes[j] >= front and indexes[j] < index:
                        indexes[j] += 1

    return result


# >>> from sbstudio.plugin.utils import _get_actions_required_to_sort_collection_with_move_method as get_moves
# >>> print(get_moves([10, 40, 30, 20, 50]))
# [(3, 1), (3, 2)]
# >>> print(get_moves([30, 20, 10, 40]))
# [(2, 0), (2, 1)]
# print(get_moves([50, 70, 40, 30, 20, 60, 10]))
# [(6, 0), (5, 1), (5, 2), (5, 3), (6, 5)]


def _get_actions_required_to_sort_collection_with_relinking(
    items: Sequence[Any], key: Optional[Callable[[Any], Any]] = None
) -> List[Any]:
    """Given a list of items and an optional sorting key function, returns a
    list of steps that are needed to sort the list when we are provided only
    with an `unlink()` method that removes an item from the list and a
    `link()` method that appends an item to the list.

    The result is a list of items; each item in this list should be unlinked
    first and then immediately re-linked.
    """
    if len(items) < 2:
        return []

    if key:
        sorted_items = sorted(items, key=key, reverse=True)
    else:
        sorted_items = sorted(items, reverse=True)

    start = 0
    items = list(items)
    while sorted_items:
        try:
            start = items.index(sorted_items[-1], start) + 1
        except ValueError:
            sorted_items.reverse()
            return sorted_items
        else:
            sorted_items.pop()
    else:
        return []


def sort_collection(collection: Collection, key: Callable[[Any], int]) -> None:
    """Sorts the given Blender collection using the given sorting key, with
    the limited set of reordering methods provided by Blender.

    The collection needs to have a method named ``move()`` that takes two
    indices and moves the item at the source index to the given target index,
    or a ``link()`` and an ``unlink()`` method where ``unlink()`` removes an
    item and ``link()`` adds the item at the end of the collection.
    """
    if hasattr(collection, "move"):
        # Collection has a move() method so we sort using that. This branch is
        # used for, e.g., bpy.data.objects["Drone 1"].constraints
        moves = _get_actions_required_to_sort_collection_with_move_method(
            collection, key
        )
        for source, target in moves:
            collection.move(source, target)  # type: ignore
    elif hasattr(collection, "link") and hasattr(collection, "unlink"):
        # Collection has no move() method but it has link() and unlink(). We
        # assume that link() adds an object at the end of the collection.
        # This branch is used for, e.g., bpy.data.collections["Formation"].objects
        items = _get_actions_required_to_sort_collection_with_relinking(collection, key)
        for item in items:
            collection.unlink(item)
            collection.link(item)
    else:
        raise TypeError("collection needs move(), link() or unlink() methods")


def filter_collection(collection: Collection, filter: Callable[[Any], bool]) -> None:
    """Filters the given Blender collection in place, keeping only those items
    that match the given filter.
    """
    to_remove: List[Any] = []
    for item in collection:
        if not filter(item):
            to_remove.append(item)

    to_remove.reverse()
    for item in to_remove:
        collection.remove(item)


def pick_unique_name(
    proposal: str,
    collection: Iterable[T],
    *,
    getter: Callable[[T], str] = attrgetter("name"),
) -> str:
    """Returns a name for a new item in the collection, starting from the given
    proposal.

    When the collection has no item with the given name, the proposal is returned
    as is. Otherwise, the longest numeric suffix of the name is incremented by
    1 until a unique name is obtained.

    Args:
        proposal: the proposed name of the new item
        collection: the collection of items
        getter: function that can be used to return the name of an item in
            the collection
    """
    existing_names = {getter(item) for item in collection}
    if proposal not in existing_names:
        return proposal

    proposal = proposal.rstrip()
    suffix = re.search("[0-9]*$", proposal)
    if suffix is None:
        return f"{proposal}.001"

    suffix = suffix.group()
    if not suffix:
        return f"{proposal}.001"

    prefix = proposal[: len(proposal) - len(suffix)]

    value = int(suffix)
    while True:
        value += 1
        new_proposal = prefix + (str(value).rjust(len(suffix), "0"))
        if new_proposal not in existing_names:
            return new_proposal
