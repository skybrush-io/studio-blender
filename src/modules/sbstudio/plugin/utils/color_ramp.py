"""Utility functions related to Blender color ramps."""


def update_color_ramp_from(target, source) -> None:
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
