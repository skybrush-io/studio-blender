"""Functions related to the handling of keyframes in animation actions."""

from collections import defaultdict
from typing import Callable, Sequence, overload

from bpy.types import Action, FCurve, Object

from .actions import (
    find_all_f_curves_for_data_path,
    find_f_curve_for_data_path,
    get_action_for_object,
    iter_all_f_curves,
)

__all__ = ("clear_keyframes", "get_keyframes", "set_keyframes")


def clear_keyframes(
    object_action_or_curve: Action | FCurve | Object,
    start: float | None = None,
    end: float | None = None,
    data_path_filter: str | Callable[[str], bool] | None = None,
):
    """Clears all the keyframes in all the F-curves of the given action in the
    given range (inclusive).
    """
    if isinstance(object_action_or_curve, Action):
        action = object_action_or_curve
        curves = iter_all_f_curves(action)
    elif isinstance(object_action_or_curve, FCurve):
        action = None
        curves = [object_action_or_curve]
    else:
        maybe_action = get_action_for_object(object_action_or_curve)
        curves = iter_all_f_curves(maybe_action)

    if isinstance(data_path_filter, str):
        data_path_filter = data_path_filter.__eq__

    for curve in curves:
        if data_path_filter is not None and not data_path_filter(curve.data_path):
            continue

        if start is None and end is None:
            curve.keyframe_points.clear()
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
                points.remove(points[index], fast=True)
            points.handles_recalc()


def get_keyframes(
    object: Object,
    data_path: str,
) -> list[tuple[float, float | list[float]]]:
    """Gets the values of all keyframes of an object at the given data path.

    Parameters:
        object: the object on which the keyframes are to be retrieved
        data_path: the data path to use

    Returns:
        the keyframes of the object at the given data path
    """
    source, sep, prop = data_path.rpartition(".")
    source = object.path_resolve(source) if sep else object

    fcurves = find_all_f_curves_for_data_path(object, data_path)

    match len(fcurves):
        case 0:
            return []
        case 1:
            return [(p.co.x, p.co.y) for p in fcurves[0].keyframe_points]
        case _:
            frames_dict = defaultdict(lambda: [0.0] * len(fcurves))
            for curve in fcurves:
                if curve.data_path == data_path:
                    for point in curve.keyframe_points:
                        frames_dict[int(point.co.x)][curve.array_index] = point.co.y
            return sorted(frames_dict.items())


@overload
def set_keyframes(
    object: Object,
    data_path: str,
    values: Sequence[tuple[float, float | None]],
    clear_range: tuple[float | None, float | None] | None = None,
    interpolation: str | None = None,
) -> list: ...


@overload
def set_keyframes(
    object: Object,
    data_path: str,
    values: Sequence[tuple[float, Sequence[float] | None]],
    clear_range: tuple[float | None, float | None] | None = None,
    interpolation: str | None = None,
) -> list: ...


def set_keyframes(
    object: Object,
    data_path: str,
    values: Sequence[tuple[float, float | Sequence[float] | None]],
    clear_range: tuple[float | None, float | None] | None = None,
    interpolation: str | None = None,
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
        return []

    is_array = any(isinstance(value[1], (tuple, list)) for value in values)

    if clear_range is not None:
        start, end = list(clear_range)
        if start is None:
            start = values[0][0]
        if end is None:
            end = values[-1][0]
        if end > start:
            clear_keyframes(object, start, end, data_path)

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
    fcurve: FCurve, values: Sequence[tuple[float, float | None]]
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
