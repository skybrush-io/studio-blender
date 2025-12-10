"""Functions related to the handling of animation actions."""

from collections.abc import Iterable
from bpy.types import Action, FCurve, Object
from typing import TYPE_CHECKING, cast

import bpy

from .utils.collections import ensure_object_exists_in_collection

if TYPE_CHECKING:
    from bpy.types import IdType

__all__ = (
    "ensure_action_exists_for_object",
    "find_all_f_curves_for_data_path",
    "find_f_curve_for_data_path",
    "find_f_curve_for_data_path_and_index",
    "get_action_for_object",
    "get_name_of_action_for_object",
    "cleanup_actions_for_object",
    "clear_all_slots_from_action",
)


def get_name_of_action_for_object(object: Object) -> str:
    """Returns the name of the action that we primarily wish to use for animating
    the properties of an object.
    """
    return f"{object.name} Action"


def ensure_action_exists_for_object(
    object: Object,
    name: str | None = None,
    *,
    clean: bool = False,
    id_type: IdType | None = None,
) -> Action:
    """Ensures that the given object has an action that can be used for
    animating the properties of the object.

    Args:
        object: the object to attach the action to
        name: the name of the action to attach to the object
        clean: whether the action is expected to be clean, i.e. should not
            already contain any F-curves. If this is true and an action
            already existed with the given name, the F-curves of the action
            will be cleared
        id_type: the type of the slot that is created for the action if it does
            not exist yet. Used only if Blender 4.4 or later is used, where
            actions are slotted.
    """
    action = get_action_for_object(object)
    if action is not None:
        return action

    if not object.animation_data:
        object.animation_data_create()

    action, _ = ensure_object_exists_in_collection(
        bpy.data.actions, name or get_name_of_action_for_object(object)
    )

    if clean:
        clear_all_slots_from_action(action)

    # Blender 4.4 switched to slotted actions, so we need to ensure that
    # the action has at least one slot.
    slot_name = f"{name} / Default slot" if name else "Default slot"
    if id_type is None:
        id_type = cast("IdType", object.id_type)
    action.slots.new(id_type=id_type, name=slot_name)

    object.animation_data.action = action

    # Blender 4.4 switched to slotted actions. We need to assign the first
    # slot of the action to the animation data. See more info here:
    #
    # https://developer.blender.org/docs/release_notes/4.4/python_api/#breaking
    if object.animation_data.action_slot is None and len(action.slots) > 0:
        object.animation_data.action_slot = action.slots[0]

    return action


def get_action_for_object(object: Object) -> Action | None:
    """Returns the animation action of the given object if it has one, or
    `None` otherwise.
    """
    if object and object.animation_data and object.animation_data.action:
        return object.animation_data.action


def _iter_all_f_curves(action: Action) -> Iterable[FCurve]:
    """Yields all F-curves in the given action."""
    return iter(action.fcurves)


def find_f_curve_for_data_path(
    object_or_action: Object | Action, data_path: str
) -> FCurve | None:
    """Finds the first F-curve in the F-curves of the action whose data path
    matches the given argument.

    Parameters:
        object_or_action: the object or action
        data_path: the data path of the F-curve we are looking for

    Returns:
        the first such F-curve or `None` if no F-curve controls the given data
        path
    """
    if not isinstance(object_or_action, Action):
        action = get_action_for_object(object_or_action)
        if not action:
            return None
    else:
        action = object_or_action

    for curve in _iter_all_f_curves(action):
        if curve.data_path == data_path:
            return curve

    return None


def find_f_curve_for_data_path_and_index(
    object_or_action: Object | Action, data_path: str, index: int
) -> FCurve | None:
    """Finds the first F-curve in the F-curves of the action whose data path
    and index match the given arguments.

    Parameters:
        object_or_action: the object or action
        data_path: the data path of the F-curve we are looking for
        index: the index of the F-curve we are looking for

    Returns:
        the first such F-curve or `None` if no F-curve controls the given data
        path and index
    """
    if not isinstance(object_or_action, Action):
        action = get_action_for_object(object_or_action)
        if not action:
            return None
    else:
        action = object_or_action

    for curve in _iter_all_f_curves(action):
        if curve.data_path == data_path and curve.array_index == index:
            return curve

    return None


def find_all_f_curves_for_data_path(
    object_or_action: Object | Action, data_path: str
) -> list[FCurve]:
    """Finds all F-curves in the F-curves of the action whose data path
    matches the given property, sorted by the array index of the curves.

    Parameters:
        object_or_action: the object or action
        data_path: the data path of the F-curves we are looking for

    Returns:
        the list of matching F-curves
    """
    if not isinstance(object_or_action, Action):
        action = get_action_for_object(object_or_action)
        if not action:
            return []
    else:
        action = object_or_action

    return sorted(
        [curve for curve in _iter_all_f_curves(action) if curve.data_path == data_path],
        key=lambda c: c.array_index,
    )


def cleanup_actions_for_object(object: Object) -> None:
    """Iterates over all F-curves in the animation data of the object and
    removes those that refer to a data path that does not exist.

    Useful for cleaning up F-curves referring to old formations and constraints
    that are not valid any more.
    """
    action = get_action_for_object(object)
    if not action:
        return

    to_delete = []
    for curve in _iter_all_f_curves(action):
        if curve.data_path:
            try:
                object.path_resolve(curve.data_path)
            except ValueError:
                to_delete.append(curve)

    while to_delete:
        action.fcurves.remove(to_delete.pop())


def clear_all_slots_from_action(action: Action) -> None:
    """Removes all F-curves from all slots of the given action."""
    slots = list(action.slots)
    for slot in slots:
        action.slots.remove(slot)
