from bpy.types import Context, Object
from collections import defaultdict
from itertools import chain
from typing import Dict, Iterable, Optional, Sequence, Tuple

from sbstudio.model.point import Point4D
from sbstudio.model.trajectory import Trajectory

from .decorators import with_context

__all__ = ("sample_positions_of_objects", "sample_positions_of_objects_in_frame_range")


@with_context
def sample_positions_of_objects(
    objects: Sequence[Object],
    frames: Iterable[int],
    *,
    by_name: bool = False,
    context: Optional[Context] = None,
) -> Dict[Object, Trajectory]:
    """Samples the positions of the given Blender objects at the given frames,
    returning a dictionary mapping the objects to their trajectories.

    Parameters:
        objects: the Blender objects to process
        frames: an iterable yielding the indices of the frames to process
        by_name: whether the result dictionary should be keyed by the _names_
            of the objects
        context: the Blender execution context; `None` means the current
            Blender context

    Returns:
        a dictionary mapping the objects to their trajectories
    """
    trajectories = defaultdict(Trajectory)
    fps = context.scene.render.fps

    for frame in frames:
        context.scene.frame_set(frame)
        for obj in objects:
            key = obj.name if by_name else obj
            trajectories[key].append(
                Point4D(frame / fps, *(obj.matrix_world.translation))
            )

    return dict(trajectories)


@with_context
def sample_positions_of_objects_in_frame_range(
    objects: Sequence[Object],
    frame_range: Tuple[int, int],
    *,
    fps: int,
    by_name: bool = False,
    context: Optional[Context] = None,
) -> Dict[Object, Trajectory]:
    """Samples the positions of the given Blender objects in the given range
    of frames, ensuring that the given minimum frames-per-second requirement
    is satisfied and that both the start and the end frames are sampled.

    Parameters:
        objects: the Blender objects to process
        frame_range: the range of frames to process; both ends are inclusive
        fps: the desired number of frames per second; the result may contain
            more samples per frame if the scene FPS is not an exact multiple
            of the desired FPS
        by_name: whether the result dictionary should be keyed by the _names_
            of the objects
        context: the Blender execution context; `None` means the current
            Blender context

    Returns:
        a dictionary mapping the objects (or their names) to their trajectories
    """
    scene_fps = context.scene.render.fps
    frame_step = max(1, int(scene_fps // fps))
    frames = chain(range(frame_range[0], frame_range[1], frame_step), [frame_range[1]])
    return sample_positions_of_objects(
        objects, frames, by_name=by_name, context=context
    )
