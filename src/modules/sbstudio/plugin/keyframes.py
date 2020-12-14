"""Functions related to the handling of keyframes in animation actions."""

from bpy.types import Action, FCurve
from operator import eq
from typing import Callable, Optional, Sequence, Tuple, Union

from .actions import find_f_curve_for_data_path, get_action_for_object

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
        data_path_filter = eq(data_path_filter)

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
    values: Sequence[Tuple[float, float]],
    clear_range: bool = False,
) -> None:
    """Sets the values of multiple keyframes to specific values, optionally
    removing any other keyframes in the range spanned by the values.

    Parameters:
        object: the object on which the keyframes are to be set
        data_path: the data path to use
        values: the values to set; it is assumed to be sorted by time
        clear_range: whether to remove any additional keyframes in the range
            spanned by the values

    Returns:
        the keyframes that were set
    """
    if clear_range and len(values) >= 2:
        frame_start, frame_end = values[0][0], values[-1][0]
        clear_keyframes(object, frame_start, frame_end, data_path)

    target, sep, prop = data_path.rpartition(".")
    target = object.path_resolve(target) if sep else object

    for frame, value in values:
        target.keyframe_insert(prop, frame=frame)

    fcurve = find_f_curve_for_data_path(object, data_path)
    assert fcurve is not None

    result = []

    if values:
        index = 0
        next_value = values[index]
        for point in fcurve.keyframe_points:
            if point.co[0] == next_value[0]:
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
