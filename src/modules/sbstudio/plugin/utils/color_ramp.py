"""Utility functions related to Blender color ramps."""

from bpy.types import ColorRamp

from typing import Any

__all__ = (
    "color_ramp_as_dict",
    "update_color_ramp_from",
    "update_color_ramp_from_dict",
)


def color_ramp_as_dict(source: ColorRamp) -> dict[str, Any]:
    """Returns a dictionary representation of a color ramp.

    Parameters:
        source: the source color ramp to export

    Returns:
        a dictionary representation of the source color ramp
    """
    return {
        "colorMode": source.color_mode,
        "interpolation": source.interpolation,
        "hueInterpolation": source.hue_interpolation,
        "elements": [
            {
                "position": element.position,
                "color": list(element.color),
                "alpha": element.alpha,
            }
            for element in source.elements
        ],
    }


def update_color_ramp_from(target: ColorRamp, source: ColorRamp) -> None:
    """Updates a color ramp from another color ramp.

    This function is needed because Blender provides no functions for creating
    a color ramp directly, or to copy a color ramp to another. This function
    effectively copies the important properties of the color ramp one by one.

    Parameters:
        target: the color ramp to update
        source: the color ramp that serves as a template for the color ramp
            being updated
    """
    target.color_mode = source.color_mode
    target.hue_interpolation = source.hue_interpolation
    target.interpolation = source.interpolation

    num_elements = len(source.elements)
    num_target_elements = len(target.elements)

    while num_target_elements < num_elements:
        target.elements.new(position=1)
        num_target_elements += 1

    for i in range(num_elements):
        target.elements[i].position = source.elements[i].position
        target.elements[i].color = source.elements[i].color
        target.elements[i].alpha = source.elements[i].alpha

    while num_target_elements > num_elements:
        target.elements.remove(target.elements[-1])
        num_target_elements -= 1


def update_color_ramp_from_dict(target: ColorRamp, data: dict[str, Any]) -> None:
    """Updates a color ramp from its dictionary representation.

    Parameters:
        target: the color ramp to update
        data: the dictionary representation of a color ramp as the data source
    """
    if color_mode := data.get("colorMode"):
        target.color_mode = color_mode

    if hue_interpolation := data.get("hueInterpolation"):
        target.hue_interpolation = hue_interpolation

    if interpolation := data.get("interpolation"):
        target.interpolation = interpolation

    if elements := data.get("elements"):
        num_elements = len(elements)
        num_target_elements = len(target.elements)

        while num_target_elements < num_elements:
            target.elements.new(position=1)
            num_target_elements += 1

        for i in range(num_elements):
            target.elements[i].position = elements[i]["position"]
            target.elements[i].color = elements[i]["color"]
            target.elements[i].alpha = elements[i]["alpha"]

        while num_target_elements > num_elements:
            target.elements.remove(target.elements[-1])
            num_target_elements -= 1
