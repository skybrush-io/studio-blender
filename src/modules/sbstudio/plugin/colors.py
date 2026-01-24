from typing import Sequence

import bpy
import numpy as np
import numpy.typing as npt
from bpy.types import CollectionObjects, Object

from sbstudio.model.types import Color, RGBAColor, RGBAColorLike
from sbstudio.plugin.actions import ensure_animation_data_exists_for_object
from sbstudio.plugin.keyframes import set_keyframes

__all__ = (
    "create_keyframe_for_color_of_drone",
    "get_color_of_drone",
    "set_color_of_drone",
)


def create_keyframe_for_color_of_drone(
    drone: Object,
    color: Color,
    *,
    frame: int | None = None,
    step: bool = False,
):
    """Creates color keyframes for the given drone to set
    in the given frame.

    Parameters:
        drone: the drone object to modify
        color: the RGB color to use for the color of the drone
        frame: the frame to apply the color on; `None` means the
            current frame
        step: whether to insert an additional keyframe in the preceding frame to
            ensure an abrupt transition
    """
    if frame is None:
        frame = bpy.context.scene.frame_current

    ensure_animation_data_exists_for_object(drone)

    color_as_rgba: RGBAColor

    if hasattr(color, "r"):
        color_as_rgba = color.r, color.g, color.b, 1.0
    else:
        color_as_rgba = color[0], color[1], color[2], 1.0

    keyframes: list[tuple[int, RGBAColor | None]] = [(frame, color_as_rgba)]
    if step and frame > bpy.context.scene.frame_start:
        keyframes.insert(0, (frame - 1, None))

    set_keyframes(drone, "color", keyframes, interpolation="LINEAR")


def get_color_of_drone(drone: Object) -> Sequence[float]:
    """Returns the color of the LED light on the given drone.

    Parameters:
        drone: the drone to query
        color: the color to apply to the LED light of the drone
    """
    if drone.color is not None:
        return drone.color

    return (0.0, 0.0, 0.0, 0.0)


def get_colors_of_drones_fast(
    drones: CollectionObjects, *, dest: npt.NDArray | None = None
) -> npt.NDArray:
    """Fetches the colors of the LED lights of the drones in the given collection.

    This function uses Blender's optimized `foreach_get()` to fill the colors
    into the provided destination array.

    The destination array must be _one-dimensional_ with length
    `len(drones) * 4`. The colors will be written in RGBA order.

    For best results, the destination array should have `dtype=np.float32`.

    Parameters:
        drones: the drones to query
        dest: the destination array to write the colors into; `None` if a new array
            should be created

    Returns:
        the destination array filled with the colors of the drones
    """
    if dest is None:
        dest = np.empty(len(drones) * 4, dtype=np.float32)
    drones.foreach_get("color", dest)
    return dest


def set_color_of_drone(drone: Object, color: RGBAColorLike):
    """Sets the color of the LED light on the given drone.

    Parameters:
        drone: the drone to update
        color: the color to apply to the LED light of the drone
    """
    if any(
        abs(a - b) > 1e-3 for a, b in zip(color, get_color_of_drone(drone), strict=True)
    ):
        drone.color = color


def set_colors_of_drones_fast(drones: CollectionObjects, colors: npt.NDArray) -> None:
    """Sets the colors of the LED lights of the drones in the given collection.

    This function uses Blender's optimized `foreach_set()` to set the colors
    from the provided array.

    The colors array must be _one-dimensional_ with length
    `len(drones) * 4`. The colors must be provided in RGBA order.

    For best results, the colors array should have `dtype=np.float32`.

    Note that setting the color property this way will not force a scene update. You
    need to force-update the scene by other means if needed.

    Parameters:
        drones: the drones to update
        colors: the array containing the colors to apply to the drones
    """
    drones.foreach_set("color", colors)
