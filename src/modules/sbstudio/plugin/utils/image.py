"""Utility functions related to Blender images."""


from sbstudio.model.types import RGBAColor


def get_pixel(image, x: int, y: int) -> RGBAColor:
    """Gets the color of a given pixel of an image."""
    width = image.size[0]
    offs = (x + y * width) * 4

    return image.pixels[offs : offs + 4]


def set_pixel(image, x: int, y: int, color: RGBAColor):
    """Sets a given pixel of an image to a given color."""
    width = image.size[0]
    offs = (x + int(y * width)) * 4
    image.pixels[offs : offs + 4] = color


def update_image_from(target, source) -> None:
    """Updates an image from another image.

    Note that this function might not work properly due to the copy limitation
    described here: https://docs.blender.org/api/current/bpy.types.Image.html

    Parameters:
        target: the target image to update
        source: the image that serves as a template for the image being updated
    """
    width, height = source.size
    target.scale(width, height)
    for i in range(len(source.pixels)):
        target.pixels[i] = source.pixels[i]
    target.update()
