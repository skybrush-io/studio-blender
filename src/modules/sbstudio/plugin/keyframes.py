"""Functions related to the handling of keyframes in animation actions."""

from bpy.types import Action, FCurve
from typing import Callable, Optional, Sequence, Tuple, Union

from .actions import (
    find_f_curve_for_data_path,
    find_all_f_curves_for_data_path,
    get_action_for_object,
)

__all__ = ("clear_keyframes", "set_keyframes")


def clear_keyframes(
    object_action_or_curve,
    start: Optional[float] = None,
    end: Optional[float] = None,
    data_path_filter: Optional[Union[str, Callable[[str], bool]]] = None,
):
    """Clears all the keyframes in all the F-curves of the given action in the
    given range (inclusive).
    """
    if isinstance(object_action_or_curve, Action):
        object = None
        action = object_action_or_curve
        curves = action.fcurves
    elif isinstance(object_action_or_curve, FCurve):
        object = None
        action = None
        curves = [object_action_or_curve]
    else:
        object = object_action_or_curve
        action = get_action_for_object(object_action_or_curve)
        curves = action.fcurves

    if isinstance(data_path_filter, str):
        data_path_filter = data_path_filter.__eq__

    for curve in curves:
        if data_path_filter is not None and not data_path_filter(curve.data_path):
            continue

        if start is None and end is None:
            if object is not None:
                object.keyframe_delete(curve.data_path)
            else:
                points = curve.keyframe_points
                for point in reversed(points):
                    points.remove(point)

        else:
            points = curve.keyframe_points
            indices_to_delete = []

            # TODO(ntamas): it would be faster to find the appropriate slice with
            # binary search
            for index, point in enumerate(points):
                time = point.co[0]
                if start is not None and time < start:
                    continue
                if end is not None and time > end:
                    break
                indices_to_delete.append(index)

            for index in reversed(indices_to_delete):
                points.remove(points[index])


def set_keyframes(
    object,
    data_path: str,
    values: Sequence[Tuple[float, Optional[Union[float, Sequence[float]]]]],
    clear_range: Optional[Tuple[Optional[float], Optional[float]]] = None,
    interpolation: Optional[str] = None,
) -> list:
    """Sets the values of multiple keyframes to specific values, optionally
    removing any other keyframes in the range spanned by the values.

    Parameters:
        object: the object on which the keyframes are to be set
        data_path: the data path to use
        values: the values to set. Each item must be a pair consisting of a
            frame number and a value, and the entire sequence is assumed to be
            sorted by time. The value may be `None` for keyframes where we want
            to keep the current value.
        clear_range: whether to remove any additional keyframes in the range
            spanned by the values. It may also be a tuple consisting of two
            frames if you want to specify the range to clear explicitly.
        interpolation: interpolation type to set for the affected keyframes;
            `None` to use the Blender default

    Returns:
        the keyframes that were added
    """
    if not values:
        return

    is_array = any(isinstance(value[1], (tuple, list)) for value in values)

    if clear_range is not None:
        clear_range = list(clear_range)
        if clear_range[0] is None:
            clear_range[0] = values[0][0]
        if clear_range[1] is None:
            clear_range[1] = values[-1][0]
        if clear_range[1] > clear_range[0]:
            clear_keyframes(object, clear_range[0], clear_range[1], data_path)

    target, sep, prop = data_path.rpartition(".")
    target = object.path_resolve(target) if sep else object

    for frame, _value in values:
        target.keyframe_insert(prop, frame=frame)

    if is_array:
        fcurves = find_all_f_curves_for_data_path(object, data_path)
        result = []
        for fcurve in fcurves:
            array_index = fcurve.array_index
            values_for_curve = [
                (frame, value[array_index] if value is not None else None)
                for frame, value in values
            ]
            result.extend(_update_keyframes_on_single_f_curve(fcurve, values_for_curve))
    else:
        fcurve = find_f_curve_for_data_path(object, data_path)
        assert fcurve is not None
        result = _update_keyframes_on_single_f_curve(fcurve, values)

    if interpolation is not None:
        for point in result:
            point.interpolation = interpolation

    return result


def _update_keyframes_on_single_f_curve(
    fcurve: FCurve, values: Sequence[Tuple[float, float]]
) -> list:
    result = []

    if values:
        index = 0
        next_value = values[index]
        for point in fcurve.keyframe_points:
            if point.co[0] == next_value[0]:
                if next_value[1] is not None:
                    point.co[1] = next_value[1]
                    point.handle_left[1] = next_value[1]
                    point.handle_right[1] = next_value[1]

                result.append(point)

                index += 1
                if index >= len(values):
                    break

                next_value = values[index]
        else:
            raise RuntimeError("Cannot set all keyframes")

    return result
