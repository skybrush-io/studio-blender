from bpy.types import Context, Object
from contextlib import contextmanager
from functools import partial
from typing import Callable, Optional, Sequence

from sbstudio.model.types import Coordinate3D

from .decorators import with_context

__all__ = ("create_position_evaluator",)


@contextmanager
@with_context
def create_position_evaluator(context: Optional[Context] = None):
    """Context manager that yields a function that allows the user to evaluate
    the position of any Blender object or objects at any given frame.

    Restores the original frame after exiting the context.
    """
    scene = context.scene
    original_frame = scene.frame_current
    seek_to = scene.frame_set

    try:
        yield partial(_evaluate_positions_of_objects, seek_to=seek_to)
    finally:
        seek_to(original_frame)


def _evaluate_positions_of_objects(
    objects: Sequence[Object],
    *,
    seek_to: Optional[Callable[[int], None]] = None,
    frame: Optional[int] = None
) -> Sequence[Coordinate3D]:
    if frame is not None:
        seek_to(frame)
    return [tuple(obj.matrix_world.translation) for obj in objects]


def get_position_of_object(object: Object) -> Coordinate3D:
    """Returns the global position of an object at the current frame.

    Parameters:
        object: a Blender object

    Returns:
        location of object in the world frame
    """
    return tuple(object.matrix_world.translation)
