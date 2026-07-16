from __future__ import annotations

from collections.abc import Callable, Sequence, Sized
from contextlib import contextmanager
from functools import partial
from math import degrees
from typing import TYPE_CHECKING, Iterator, Protocol, overload

import numpy as np
import numpy.typing as npt
from bpy.types import CollectionObjects, Context, Object
from mathutils import Vector
from numpy import float32
from numpy.typing import NDArray

from sbstudio.model.types import Coordinate3D, Quaternion, Rotation3D, SupportsForEach

from .decorators import with_context

if TYPE_CHECKING:
    from mathutils import Vector

__all__ = (
    "create_position_evaluator",
    "get_position_of_object",
    "get_positions_of_objects_fast",
    "get_xyz_euler_rotation_of_object",
    "get_quaternion_rotation_of_object",
    "ObjectPositions",
)


class PositionEvaluator(Protocol):
    """A callable that evaluates the positions of Blender objects at a given frame."""

    def __call__(
        self,
        objects: Sequence[Object],
        *,
        frame: int | None = None,
    ) -> Sequence[Coordinate3D]: ...


@contextmanager
@with_context
def create_position_evaluator(
    context: Context | None = None,
) -> Iterator[PositionEvaluator]:
    """Context manager that yields a function that allows the user to evaluate
    the position of any Blender object or objects at any given frame.

    Restores the original frame after exiting the context.
    """
    assert context is not None

    scene = context.scene
    original_frame = scene.frame_current
    seek_to = scene.frame_set

    try:
        yield partial(_evaluate_positions_of_objects, seek_to=seek_to)  # ty:ignore[invalid-yield]
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
    """Returns the global position of an object at the current frame as a tuple of
    length 3.

    Parameters:
        object: a Blender object

    Returns:
        location of object in the world frame
    """
    return tuple(object.matrix_world.translation)  # ty:ignore[invalid-return-type]


def get_position_of_object_as_vector(object: Object) -> Vector:
    """Returns the global position of an object at the current frame as a native
    Blender `mathutils.Vector`.

    This functions is provided because certain Blender APIs (e.g, `mathutils.bvhtree`)
    contain specialized code paths for vectors.

    Parameters:
        object: a Blender object

    Returns:
        location of object in the world frame
    """
    return object.matrix_world.translation


def get_xyz_euler_rotation_of_object(object: Object) -> Rotation3D:
    """Returns the global rotation of an object at the current frame
    in XYZ Euler order, in degrees.

    Parameters:
        object: a Blender object

    Returns:
        rotation of object in the world frame, in degrees
    """
    return tuple(degrees(angle) for angle in object.matrix_world.to_euler("XYZ"))  # ty:ignore[invalid-return-type]


def get_quaternion_rotation_of_object(object: Object) -> Quaternion:
    """Returns the global rotation of an object at the current frame
    in quaternions.

    Parameters:
        object: a Blender object

    Returns:
        rotation of object in the world frame, in quaternions.
    """
    return tuple(object.matrix_world.to_quaternion())  # ty:ignore[invalid-return-type]


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
    objects.foreach_get("matrix_world", matrices.ravel())  # ty:ignore[no-matching-overload]
    if dest is None:
        return matrices[:, 12:15]
    else:
        np.copyto(dest, matrices[:, 12:15])
        return dest


class ObjectPositions(Sized):
    """Object that holds the positions of multiple objects in two formats: as a NumPy
    array and as a list of Blender `mathutils.Vector` objects.

    This object is useful for cases when the same list of positions has to be passed
    on to NumPy and `mathutils` APIs at the same time; NumPy arrays are faster with
    NumPy functions while vectors are faster with `mathutils` APIs.
    """

    _as_array: NDArray[float32] | None = None
    """NumPy array of shape (N, 3) and dtype `float32` containing the positions."""

    _as_vectors: list[Vector] | None = None
    """List of Blender `mathutils.Vector` objects corresponding to the positions.
    Constructed on the fly when first accessed.
    """

    _objects: CollectionObjects
    """Reference to the Blender collection from which the positions were constructed,
    if any. Used to produce the position vectors more efficiently when this is known.
    """

    def __init__(self, objects: CollectionObjects):
        """Constructor.

        Parameters:
            objects: a Blender collection holding the objects
        """
        self._objects = objects

    @property
    def as_array(self) -> NDArray[float32]:
        """Returns the positions as a NumPy array of shape (N, 3) and dtype `float32`."""
        if self._as_array is None:
            self._as_array = get_positions_of_objects_fast(self._objects)
        return self._as_array

    @property
    def as_vectors(self) -> Sequence[Vector]:
        """Returns the positions as a list of Blender `mathutils.Vector` objects."""
        if self._as_vectors is None:
            self._as_vectors = [obj.matrix_world.translation for obj in self._objects]
        return self._as_vectors

    @property
    def as_coordinate_sequence(self) -> Sequence[Coordinate3D]:
        """Returns the positions as a sequence of Coordinate3D_ objects.

        Since the only guarantee about a Coordinate3D_ object is that it behaves like
        a tuple of length 3, we are free to return the NumPy array or the list of
        vectors. If one of these is already constructed, we return that; otherwise, we
        construct the array and return that.
        """
        if self._as_vectors is not None:
            return self._as_vectors  # ty:ignore[invalid-return-type]
        else:
            return self.as_array  # ty:ignore[invalid-return-type]

    def __len__(self) -> int:
        """Returns the number of positions stored in this object."""
        return len(self._objects)
