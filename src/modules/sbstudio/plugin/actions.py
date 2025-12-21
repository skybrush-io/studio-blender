"""Functions related to the handling of animation actions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

import bpy
from bpy.types import (
    Action,
    ActionChannelbag,
    ActionKeyframeStrip,
    AnimData,
    FCurve,
    Object,
)

from .utils.collections import ensure_object_exists_in_collection

if TYPE_CHECKING:
    from bpy.types import IdType  # not a real type


__all__ = (
    "ensure_animation_data_exists_for_object",
    "ensure_f_curve_exists_for_data_path_and_index",
    "find_all_f_curves_for_data_path",
    "find_f_curve_for_data_path",
    "find_f_curve_for_data_path_and_index",
    "get_action_for_object",
    "get_animation_data_for_object",
    "iter_all_f_curves",
    "cleanup_actions_for_object",
    "clear_all_slots_from_action",
)


def ensure_animation_data_exists_for_object(
    object: Object,
    name: str | None = None,
    *,
    clean: bool = False,
    id_type: IdType | None = None,
) -> AnimData:
    """Ensures that the given object has an action that can be used for
    animating the properties of the object.

    Args:
        object: the object to attach the action to
        name: the name of the action to attach to the object; `None` means
            to use a default name
        clean: whether the action is expected to be clean, i.e. should not
            already contain any F-curves. If this is true and an action
            already existed with the given name, the F-curves of the action
            will be cleared
        id_type: the type of the slot that is created for the action if it does
            not exist yet

    Returns:
        the animation data of the object
    """
    if name is None:
        name = f"Animation data for {object.name}"

    _ensure_action_exists_for_object(object, name, clean=clean, id_type=id_type)

    assert object.animation_data is not None
    return object.animation_data


def _ensure_action_exists_for_object(
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
            not exist yet
    """
    action = get_action_for_object(object)
    if action is not None:
        return action

    if not object.animation_data:
        object.animation_data_create()

    action, _ = ensure_object_exists_in_collection(
        bpy.data.actions, name or _get_name_of_action_for_object(object)
    )

    if clean:
        clear_all_slots_from_action(action)

    return action


def _get_name_of_action_for_object(object: Object) -> str:
    """Returns the name of the action that we primarily wish to use for animating
    the properties of an object.
    """
    return f"{object.name} Action"


def get_action_for_object(object: Object) -> Action | None:
    """Returns the animation action of the given object if it has one, or
    `None` otherwise.
    """
    if object and object.animation_data and object.animation_data.action:
        return object.animation_data.action


def get_animation_data_for_object(object: Object) -> AnimData | None:
    """Returns the animation data of the given object if it has one, or
    `None` otherwise.
    """
    return object.animation_data


def _get_channelbag_from_animation_data(
    anim_data: AnimData | None,
) -> ActionChannelbag | None:
    """Returns the channelbag containing the animation F-curves of the active slot of
    the action of the given animation data object.

    Args:
        anim_data: the animation data
    """
    if anim_data is None:
        return None

    action = anim_data.action

    if action and len(action.layers) > 0 and len(action.layers[0].strips) > 0:
        # An action may not have more than one layer at the moment, and a layer
        # may not have more than one strip at the moment, so we just access the
        # first strip of the first layer.
        strip = cast("ActionKeyframeStrip", action.layers[0].strips[0])
        slot = anim_data.action_slot
        if slot is None:
            # If we have no slot, we fall back to the legacy behaviour of
            # retrieving the channel bag from the first slot of the action.
            if len(action.slots) == 0:
                return None
            slot = action.slots[0]

        bag = strip.channelbag(slot)
        return bag
    else:
        # If we have no action, we obviously need to return None. We also need
        # to return None if we have no layers or strips, because a channel bag
        # cannot exist without a strip.
        return None


def iter_all_f_curves(anim_data: AnimData | None) -> Iterable[FCurve]:
    """Yields all F-curves in the given animation data object.

    Only the active action and slot of the animation data are considered.
    """
    bag = _get_channelbag_from_animation_data(anim_data)
    return iter(bag.fcurves) if bag else iter(())


def _iter_all_f_curves_and_bags(
    anim_data: AnimData | None,
) -> Iterable[tuple[FCurve, ActionChannelbag]]:
    """Yields all F-curves in the given action along with the channel bag that
    they belong to.
    """
    bag = _get_channelbag_from_animation_data(anim_data)
    return iter((curve, bag) for curve in bag.fcurves) if bag else iter(())


def find_f_curve_for_data_path(
    anim_data: AnimData | None, data_path: str
) -> FCurve | None:
    """Finds the first F-curve in the F-curves of the given animation data whose data
    path matches the given argument.

    Only the active action and slot of the animation data are considered.

    Parameters:
        anim_data: the animation data
        data_path: the data path of the F-curve we are looking for

    Returns:
        the first such F-curve or `None` if no F-curve controls the given data
        path
    """
    for curve in iter_all_f_curves(anim_data):
        if curve.data_path == data_path:
            return curve

    return None


def find_f_curve_for_data_path_and_index(
    anim_data: AnimData | None, data_path: str, index: int
) -> FCurve | None:
    """Finds the first F-curve in the F-curves of the given animation data whose data
    path and index match the given arguments.

    Only the active action and slot of the animation data are considered.

    Parameters:
        anim_data: the animation data
        data_path: the data path of the F-curve we are looking for
        index: the index of the F-curve we are looking for

    Returns:
        the first such F-curve or `None` if no F-curve controls the given data
        path and index
    """
    for curve in iter_all_f_curves(anim_data):
        if curve.data_path == data_path and curve.array_index == index:
            return curve

    return None


def find_all_f_curves_for_data_path(
    anim_data: AnimData | None, data_path: str
) -> list[FCurve]:
    """Finds all F-curves in the F-curves of the given animation data whose data
    path matches the given property, sorted by the array index of the curves.

    Only the active action and slot of the animation data are considered.

    Parameters:
        anim_data: the animation data
        data_path: the data path of the F-curves we are looking for

    Returns:
        the list of matching F-curves
    """
    return sorted(
        [
            curve
            for curve in iter_all_f_curves(anim_data)
            if curve.data_path == data_path
        ],
        key=lambda c: c.array_index,
    )


def ensure_f_curve_exists_for_data_path_and_index(
    object: Object, *, data_path: str, index: int
) -> FCurve:
    """Finds the first F-curve in the F-curves of the object whose data path
    and index match the given arguments, creating one if it does not exist yet.

    Parameters:
        object: the object to retrieve the action from
        data_path: the data path of the F-curve we are looking for
        index: the index of the F-curve we are looking for

    Returns:
        the F-curve
    """
    action = _ensure_action_exists_for_object(object)
    return action.fcurve_ensure_for_datablock(object, data_path, index=index)


def cleanup_actions_for_object(object: Object) -> None:
    """Iterates over all F-curves in the animation data of the object and
    removes those that refer to a data path that does not exist.

    Useful for cleaning up F-curves referring to old formations and constraints
    that are not valid any more.
    """
    anim_data = get_animation_data_for_object(object)
    if not anim_data:
        return

    to_delete = []
    for curve, bag in _iter_all_f_curves_and_bags(anim_data):
        if curve.data_path:
            try:
                object.path_resolve(curve.data_path)
            except ValueError:
                to_delete.append((bag, curve))

    while to_delete:
        bag, curve = to_delete.pop()
        bag.remove(curve)


def clear_all_slots_from_action(action: Action) -> None:
    """Removes all F-curves from all slots of the given action."""
    slots = list(action.slots)
    for slot in slots:
        action.slots.remove(slot)
