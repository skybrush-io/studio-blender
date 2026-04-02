from collections.abc import Callable, Sequence
from contextlib import contextmanager
from functools import partial
from math import degrees
from typing import Iterator, overload

import numpy as np
import numpy.typing as npt
from bpy.types import Context, Object

from sbstudio.model.types import Coordinate3D, Quaternion, Rotation3D, SupportsForEach

from .decorators import with_context

__all__ = (
    "create_position_evaluator",
    "get_position_of_object",
    "get_xyz_euler_rotation_of_object",
    "get_quaternion_rotation_of_object",
)


@contextmanager
@with_context
def create_position_evaluator(
    context: Context | None = None,
) -> Iterator[Callable[[Sequence[Object]], Sequence[Coordinate3D]]]:
    """Context manager that yields a function that allows the user to evaluate
    the position of any Blender object or objects at any given frame.

    Restores the original frame after exiting the context.
    """
    assert context is not None

    scene = context.scene
    original_frame = scene.frame_current
    seek_to = scene.frame_set

    try:
        yield partial(_evaluate_positions_of_objects, seek_to=seek_to)
    finally:
        seek_to(original_frame)


@overload
def _evaluate_positions_of_objects(
    objects: Sequence[Object],
) -> Sequence[Coordinate3D]: ...


@overload
def _evaluate_positions_of_objects(
    objects: Sequence[Object],
    *,
    seek_to: Callable[[int], None],
    frame: int,
) -> Sequence[Coordinate3D]: ...


def _evaluate_positions_of_objects(
    objects: Sequence[Object],
    *,
    seek_to: Callable[[int], None] | None = None,
    frame: int | None = None,
) -> Sequence[Coordinate3D]:
    if frame is not None:
        assert seek_to is not None
        seek_to(frame)
    return [get_position_of_object(obj) for obj in objects]


def get_position_of_object(object: Object) -> Coordinate3D:
    """Returns the global position of an object at the current frame.

    Parameters:
        object: a Blender object

    Returns:
        location of object in the world frame
    """
    return tuple(object.matrix_world.translation)  # type: ignore[reportReturnType]


def get_xyz_euler_rotation_of_object(object: Object) -> Rotation3D:
    """Returns the global rotation of an object at the current frame
    in XYZ Euler order, in degrees.

    Parameters:
        object: a Blender object

    Returns:
        rotation of object in the world frame, in degrees
    """
    return tuple(degrees(angle) for angle in object.matrix_world.to_euler("XYZ"))  # type: ignore[invalid-return-type]


def get_quaternion_rotation_of_object(object: Object) -> Quaternion:
    """Returns the global rotation of an object at the current frame
    in quaternions.

    Parameters:
        object: a Blender object

    Returns:
        rotation of object in the world frame, in quaternions.
    """
    return tuple(object.matrix_world.to_quaternion())  # type: ignore[invalid-return-type]


def get_positions_of_objects_fast(
    objects: SupportsForEach, *, dest: npt.NDArray | None = None
) -> npt.NDArray:
    """Returns the global positions of the objects in the given collection at the
    current frame.

    This function uses Blender's optimized `foreach_get()` to fill the positions
    into the provided destination array.

    The destination array must have `len(drones) * 3` elements. The positions will be
    written in XYZ order. For best results, the destination array should have
    `dtype=np.float32`.

    Due to Blender's internal storage of matrices, this function fetches the full
    4x4 transformation matrices of the objects and extracts the translation components
    from them. This means that a new NumPy array will be allocated even if the caller
    provides a destination array.

    Parameters:
        objects: a Blender collection holding the objects
        dest: the destination array to write the positions into; `None` if a new array
            should be created

    Returns:
        locations of object in the world frame
    """
    matrices = np.empty((len(objects), 16), dtype=np.float32)
    objects.foreach_get("matrix_world", matrices.ravel())
    if dest is None:
        return matrices[:, 12:15]
    else:
        np.copyto(dest, matrices[:, 12:15])
        return dest
