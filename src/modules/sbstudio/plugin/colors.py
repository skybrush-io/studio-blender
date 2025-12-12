import bpy
from bpy.types import Object

from sbstudio.model.types import RGBAColor, RGBAColorLike
from sbstudio.plugin.actions import ensure_action_exists_for_object
from sbstudio.plugin.keyframes import set_keyframes

__all__ = (
    "create_keyframe_for_color_of_drone",
    "get_color_of_drone",
    "set_color_of_drone",
)

is_blender_4 = bpy.app.version >= (4, 0, 0)


def create_keyframe_for_color_of_drone(
    drone: Object,
    color: tuple[float, float, float] | tuple[float, float, float, float] | RGBAColor,
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

    ensure_action_exists_for_object(drone)

    if hasattr(color, "r"):
        color_as_rgba = color.r, color.g, color.b, 1.0
    else:
        color_as_rgba = color[0], color[1], color[2], 1.0

    keyframes: list[tuple[int, RGBAColor | None]] = [(frame, color_as_rgba)]
    if step and frame > bpy.context.scene.frame_start:
        keyframes.insert(0, (frame - 1, None))

    set_keyframes(drone, "color", keyframes, interpolation="LINEAR")


def get_color_of_drone(drone) -> RGBAColor:
    """Returns the color of the LED light on the given drone.

    Parameters:
        drone: the drone to query
        color: the color to apply to the LED light of the drone
    """
    if drone.color is not None:
        return drone.color

    return (0.0, 0.0, 0.0, 0.0)


def set_color_of_drone(drone, color: RGBAColorLike):
    """Sets the color of the LED light on the given drone.

    Parameters:
        drone: the drone to update
        color: the color to apply to the LED light of the drone
    """
    drone.color = color
