import bpy

from bpy.types import Context, Object
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence

from sbstudio.model.color import Color4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.point import Point4D
from sbstudio.model.trajectory import Trajectory
from sbstudio.model.yaw import YawSetpoint, YawSetpointList
from sbstudio.plugin.colors import get_color_of_drone
from sbstudio.plugin.utils.evaluator import (
    get_position_of_object,
    get_xyz_euler_rotation_of_object,
)
from sbstudio.plugin.utils.progress import FrameIterator, FrameProgressReport

from .decorators import with_context

__all__ = (
    "each_frame_in",
    "frame_range",
    "sample_colors_of_objects",
    "sample_positions_of_objects",
    "sample_positions_and_yaw_of_objects",
    "sample_positions_of_objects_in_frame_range",
    "sample_positions_and_colors_of_objects",
    "sample_positions_colors_and_yaw_of_objects",
)


def _to_int_255(value: float) -> int:
    """Convert [0,1] float to clamped [0,255] int."""
    return int(max(0, min(255, round(value * 255))))


@with_context
def frame_range(
    start: int,
    end: int,
    *,
    fps: int,
    context: Context | None = None,
    operation: str | None = None,
    progress: Callable[[FrameProgressReport], None] | None = None,
) -> Iterator[int]:
    """Generator that iterates from the given start frame to the given end frame
    with the given number of frames per second.
    """
    assert context is not None  # injected

    scene_fps = context.scene.render.fps
    frame_step = max(1, int(scene_fps // fps))
    return FrameIterator(start, end, frame_step, operation=operation, progress=progress)


@with_context
def each_frame_in(
    frames: Iterable[int], *, redraw: bool = False, context: Context | None = None
) -> Iterable[tuple[int, float]]:
    """Generator that iterates over the given frames, sets the current frame in
    Blender to each frame one by one, and then yields a tuple consisting of
    the current frame _index_ and the current frame _timestamp_ to the caller.

    Args:
        frames: the frames to iterate over
        redraw: whether to redraw the Blender window after each frame is set.
            Makes the iteration significantly slower.
    """
    assert context is not None  # injected

    scene = context.scene
    fps = scene.render.fps

    for frame in frames:
        scene.frame_set(frame)
        if redraw:
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=0)

        time = frame / fps
        yield frame, time


@with_context
def sample_positions_of_objects(
    objects: Sequence[Object],
    frames: Iterable[int],
    *,
    by_name: bool = False,
    simplify: bool = False,
    context: Context | None = None,
) -> dict[Object, Trajectory]:
    """Samples the positions of the given Blender objects at the given frames,
    returning a dictionary mapping the objects to their trajectories.

    Parameters:
        objects: the Blender objects to process
        frames: an iterable yielding the indices of the frames to process
        by_name: whether the result dictionary should be keyed by the _names_
            of the objects
        context: the Blender execution context; `None` means the current
            Blender context
        simplify: whether to simplify the trajectories. If this option is
            enabled, the resulting trajectories might not contain samples for
            all the input frames; excess samples that are identical to previous
            ones will be removed.

    Returns:
        a dictionary mapping the objects to their trajectories
    """
    trajectories = defaultdict(Trajectory)

    for _, time in each_frame_in(frames, context=context):
        for obj in objects:
            key = obj.name if by_name else obj
            trajectories[key].append(Point4D(time, *get_position_of_object(obj)))

    if simplify:
        return {key: value.simplify_in_place() for key, value in trajectories.items()}
    else:
        return dict(trajectories)


@with_context
def sample_positions_and_yaw_of_objects(
    objects: Sequence[Object],
    frames: Iterable[int],
    *,
    by_name: bool = False,
    simplify: bool = False,
    context: Context | None = None,
) -> dict[Object, tuple[Trajectory, YawSetpointList]]:
    """Samples the positions of the given Blender objects at the given frames,
    returning a dictionary mapping the objects to their trajectories.

    Parameters:
        objects: the Blender objects to process
        frames: an iterable yielding the indices of the frames to process
        by_name: whether the result dictionary should be keyed by the _names_
            of the objects
        context: the Blender execution context; `None` means the current
            Blender context
        simplify: whether to simplify the trajectories. If this option is
            enabled, the resulting trajectories might not contain samples for
            all the input frames; excess samples that are identical to previous
            ones will be removed.

    Returns:
        a dictionaries mapping the objects to their trajectories and yaw setpoints
    """
    trajectories = defaultdict(Trajectory)
    yaw_setpoints = defaultdict(YawSetpointList)

    for _, time in each_frame_in(frames, context=context):
        for obj in objects:
            key = obj.name if by_name else obj
            trajectories[key].append(Point4D(time, *get_position_of_object(obj)))
            rotation = get_xyz_euler_rotation_of_object(obj)
            # note the conversion from Blender CCW to Skybrush CW representation
            yaw_setpoints[key].append(YawSetpoint(time, -rotation[2]))

    # Ensure that the yaw curve makes sense even if the extracted yaw angles
    # "wrap around" the boundary between -180 and 180 degrees
    for yaw in yaw_setpoints.values():
        yaw.unwrap()

    if simplify:
        return {
            key: (
                trajectory.simplify_in_place(),
                yaw_setpoints[key].simplify(),
            )
            for key, trajectory in trajectories.items()
        }

    else:
        return {
            key: (trajectory, yaw_setpoints[key])
            for key, trajectory in trajectories.items()
        }


@with_context
def sample_colors_of_objects(
    objects: Sequence[Object],
    frames: Iterable[int],
    *,
    by_name: bool = False,
    simplify: bool = False,
    redraw: bool = False,
    context: Context | None = None,
) -> dict[Object | str, LightProgram]:
    """Samples the colors of the given Blender objects at the given frames,
    returning a dictionary mapping the objects to their light programs.

    Parameters:
        objects: the Blender objects to process
        frames: an iterable yielding the indices of the frames to process
        by_name: whether the result dictionary should be keyed by the _names_
            of the objects
        simplify: whether to simplify the light programs. If this option is
            enabled, the resulting light program might not contain samples
            for all the input frames; excess samples that are identical to
            previous ones will be removed.
        redraw: whether to redraw the Blender window after each frame is set
            (this is necessary to ensure that the light colors are updated
            correctly for video-based light effects)
        context: the Blender execution context; `None` means the current
            Blender context

    Returns:
        a dictionary mapping the objects to their light programs
    """
    lights = defaultdict(LightProgram)

    for _, time in each_frame_in(frames, context=context, redraw=redraw):
        for obj in objects:
            key = obj.name if by_name else obj
            color = get_color_of_drone(obj)
            lights[key].append(
                Color4D(
                    time,
                    _to_int_255(color[0]),
                    _to_int_255(color[1]),
                    _to_int_255(color[2]),
                )
            )

    if simplify:
        return {key: value.simplify() for key, value in lights.items()}
    else:
        return dict(lights)


@with_context
def sample_positions_and_colors_of_objects(
    objects: Sequence[Object],
    frames: Iterable[int],
    *,
    by_name: bool = False,
    simplify: bool = False,
    redraw: bool = False,
    context: Context | None = None,
) -> dict[Object, tuple[Trajectory, LightProgram]]:
    """Samples the positions and colors of the given Blender objects at the
    given frames, returning a dictionary mapping the objects to their
    trajectories and light programs.

    Parameters:
        objects: the Blender objects to process
        frames: an iterable yielding the indices of the frames to process
        by_name: whether the result dictionary should be keyed by the _names_
            of the objects
        simplify: whether to simplify the trajectories and light programs. If
            this option is enabled, the resulting trajectories and light programs
            might not contain samples for all the input frames; excess samples
            that are identical to previous ones will be removed.
        redraw: whether to redraw the Blender window after each frame is set
            (this is necessary to ensure that the light colors are updated
            correctly for video-based light effects)
        context: the Blender execution context; `None` means the current
            Blender context

    Returns:
        a dictionary mapping the objects to their trajectories and light programs
    """
    trajectories = defaultdict(Trajectory)
    lights = defaultdict(LightProgram)

    for _, time in each_frame_in(frames, context=context, redraw=redraw):
        for obj in objects:
            key = obj.name if by_name else obj
            pos = get_position_of_object(obj)
            color = get_color_of_drone(obj)
            trajectories[key].append(Point4D(time, *pos))
            lights[key].append(
                Color4D(
                    time,
                    _to_int_255(color[0]),
                    _to_int_255(color[1]),
                    _to_int_255(color[2]),
                )
            )

    if simplify:
        return {
            key: (trajectory.simplify_in_place(), lights[key].simplify())
            for key, trajectory in trajectories.items()
        }
    else:
        return {
            key: (trajectory, lights[key]) for key, trajectory in trajectories.items()
        }


@with_context
def sample_positions_colors_and_yaw_of_objects(
    objects: Sequence[Object],
    frames: Iterable[int],
    *,
    by_name: bool = False,
    simplify: bool = False,
    redraw: bool = False,
    context: Context | None = None,
) -> dict[Object, tuple[Trajectory, LightProgram, YawSetpointList]]:
    """Samples the positions, colors and yaw angles of the given Blender objects
    at the given frames, returning a dictionary mapping the objects to their
    trajectories, light programs and yaw setpoints.

    Parameters:
        objects: the Blender objects to process
        frames: an iterable yielding the indices of the frames to process
        by_name: whether the result dictionary should be keyed by the _names_
            of the objects
        simplify: whether to simplify the trajectories, light programs and yaw
            setpoints. If this option is enabled, the resulting trajectories,
            light programs and yaw setpoints might not contain samples for all
            the input frames; excess samples that are identical to previous
            ones will be removed.
        redraw: whether to redraw the Blender window after each frame is set
            (this is necessary to ensure that the light colors are updated
            correctly for video-based light effects)
        context: the Blender execution context; `None` means the current
            Blender context

    Returns:
        a dictionary mapping the objects to their trajectories and light programs
    """
    trajectories = defaultdict(Trajectory)
    lights = defaultdict(LightProgram)
    yaw_setpoints = defaultdict(YawSetpointList)

    for _, time in each_frame_in(frames, context=context, redraw=redraw):
        for obj in objects:
            key = obj.name if by_name else obj
            pos = get_position_of_object(obj)
            color = get_color_of_drone(obj)
            rotation = get_xyz_euler_rotation_of_object(obj)
            trajectories[key].append(Point4D(time, *pos))
            lights[key].append(
                Color4D(
                    time,
                    _to_int_255(color[0]),
                    _to_int_255(color[1]),
                    _to_int_255(color[2]),
                )
            )
            # note the conversion from Blender CCW to Skybrush CW representation
            yaw_setpoints[key].append(YawSetpoint(time, -rotation[2]))

    # Ensure that the yaw curve makes sense even if the extracted yaw angles
    # "wrap around" the boundary between -180 and 180 degrees
    for yaw in yaw_setpoints.values():
        yaw.unwrap()

    if simplify:
        return {
            key: (
                trajectory.simplify_in_place(),
                lights[key].simplify(),
                yaw_setpoints[key].simplify(),
            )
            for key, trajectory in trajectories.items()
        }
    else:
        return {
            key: (trajectory, lights[key], yaw_setpoints[key])
            for key, trajectory in trajectories.items()
        }


@with_context
def sample_positions_of_objects_in_frame_range(
    objects: Sequence[Object],
    bounds: tuple[int, int],
    *,
    fps: int,
    by_name: bool = False,
    simplify: bool = False,
    context: Context | None = None,
) -> dict[Object, Trajectory]:
    """Samples the positions of the given Blender objects in the given range
    of frames, ensuring that the given minimum frames-per-second requirement
    is satisfied and that both the start and the end frames are sampled.

    Parameters:
        objects: the Blender objects to process
        bounds: the range of frames to process; both ends are inclusive
        fps: the desired number of frames per second; the result may contain
            more samples per frame if the scene FPS is not an exact multiple
            of the desired FPS
        by_name: whether the result dictionary should be keyed by the _names_
            of the objects
        simplify: whether to simplify the trajectories. If this option is
            enabled, the resulting trajectories might not contain samples for
            all the input frames; excess samples that are identical to previous
            ones will be removed.
        context: the Blender execution context; `None` means the current
            Blender context

    Returns:
        a dictionary mapping the objects (or their names) to their trajectories
    """
    return sample_positions_of_objects(
        objects,
        frame_range(bounds[0], bounds[1], fps=fps, context=context),
        by_name=by_name,
        simplify=simplify,
        context=context,
    )
