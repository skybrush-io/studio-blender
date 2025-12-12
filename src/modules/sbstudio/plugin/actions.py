"""Functions related to the handling of animation actions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

import bpy
from bpy.types import Action, ActionSlot, FCurve, Object

from .utils.collections import ensure_object_exists_in_collection

if TYPE_CHECKING:
    from bpy.types import ActionChannelbag, ActionKeyframeStrip, IdType

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


def _get_channelbag_from_action(
    action: Action | None, *, slot: ActionSlot | None = None
) -> ActionChannelbag | None:
    """Returns the channelbag containing the animation F-curves corresponding to
    the given action.

    Args:
        action: the action whose channel bag we wish to retrieve.
        slot: the active slot of the animation data that owns the action, if known.
            `None` means that we fall back to the legacy behaviour in Blender before
            the migration to the new "slotted" action system, retrieving the channel
            bag of the first slot of the action from the first (and only) strip of
            the first (and only) layer of the action.
    """
    if action and len(action.layers) > 0 and len(action.layers[0].strips) > 0:
        # An action may not have more than one layer at the moment, and a layer
        # may not have more than one strip at the moment, so we just access the
        # first strip of the first layer.
        strip = cast("ActionKeyframeStrip", action.layers[0].strips[0])
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


def add_new_f_curve(action: Action, *, data_path: str, index: int = 0) -> FCurve:
    """Adds a new F-curve to the given action for the given data path and
    index.
    """
    bag = _get_channelbag_from_action(action)
    if bag is None:
        # TODO(ntamas): create the channel bag if it does not exist yet
        raise RuntimeError("Could not get channel bag from action")

    curve = bag.fcurves.new(data_path=data_path, index=index)
    return curve


def iter_all_f_curves(
    action: Action | None,
) -> Iterable[FCurve]:
    """Yields all F-curves in the given action."""
    bag = _get_channelbag_from_action(action)
    return iter(bag.fcurves) if bag else iter(())


def iter_all_f_curves_and_bags(
    action: Action | None,
) -> Iterable[tuple[FCurve, ActionChannelbag]]:
    """Yields all F-curves in the given action along with the channel bag that
    they belong to.
    """
    bag = _get_channelbag_from_action(action)
    return iter((curve, bag) for curve in bag.fcurves) if bag else iter(())


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

    for curve in iter_all_f_curves(action):
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

    for curve in iter_all_f_curves(action):
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
        [curve for curve in iter_all_f_curves(action) if curve.data_path == data_path],
        key=lambda c: c.array_index,
    )


def ensure_f_curve_exists_for_data_path_and_index(
    action: Action, *, data_path: str, index: int
) -> FCurve | None:
    """Finds the first F-curve in the F-curves of the action whose data path
    and index match the given arguments, creating one if it does not exist yet.

    Parameters:
        action: the action to retrieve the F-curve from
        data_path: the data path of the F-curve we are looking for
        index: the index of the F-curve we are looking for

    Returns:
        the F-curve
    """
    return find_f_curve_for_data_path_and_index(
        action, data_path=data_path, index=index
    ) or add_new_f_curve(action, data_path=data_path, index=index)


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
    for curve, bag in iter_all_f_curves_and_bags(action):
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
