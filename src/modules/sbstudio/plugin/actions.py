"""Functions related to the handling of animation actions."""

from bpy.types import Action, FCurve
from typing import Optional

import bpy

from .utils.collections import ensure_object_exists_in_collection

__all__ = (
    "ensure_action_exists_for_object",
    "find_all_f_curves_for_data_path",
    "find_f_curve_for_data_path",
    "find_f_curve_for_data_path_and_index",
    "get_action_for_object",
    "get_name_of_action_for_object",
)


def get_name_of_action_for_object(object) -> str:
    """Returns the name of the action that we primarily wish to use for animating
    the properties of an object.
    """
    return f"{object.name} Action"


def ensure_action_exists_for_object(object, name: Optional[str] = None) -> Action:
    """Ensures that the given object has an action that can be used for
    animating the properties of the object.
    """
    action = get_action_for_object(object)
    if action is not None:
        return action

    if not object.animation_data:
        object.animation_data_create()

    action, _ = ensure_object_exists_in_collection(
        bpy.data.actions, name or get_name_of_action_for_object(object)
    )
    object.animation_data.action = action

    return action


def get_action_for_object(object) -> Action:
    """Returns the animation action of the given object if it has one, or
    `None` otherwise.
    """
    if object and object.animation_data and object.animation_data.action:
        return object.animation_data.action


def find_f_curve_for_data_path(object_or_action, data_path: str) -> Optional[FCurve]:
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

    for curve in action.fcurves:
        if curve.data_path == data_path:
            return curve

    return None


def find_f_curve_for_data_path_and_index(
    object_or_action, data_path: str, index: int
) -> Optional[FCurve]:
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

    for curve in action.fcurves:
        if curve.data_path == data_path and curve.array_index == index:
            return curve

    return None


def find_all_f_curves_for_data_path(
    object_or_action, data_path: str
) -> Optional[FCurve]:
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

    # TODO(ntamas): sort by array index!
    result = [curve for curve in action.fcurves if curve.data_path == data_path]
    return result
