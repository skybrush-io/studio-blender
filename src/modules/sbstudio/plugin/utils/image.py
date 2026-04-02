"""Utility functions related to Blender images."""

import bpy
from bpy.types import Image

from sbstudio.model.types import RGBAColor

__all__ = ["convert_from_srgb_to_linear", "find_image_by_name", "get_pixel"]


def convert_from_srgb_to_linear(color: RGBAColor) -> RGBAColor:
    """Converts a color from sRGB to linear space.

    Args:
        color: The color to convert.

    Returns:
        The converted color.
    """
    # Note to ourselves: Blender has a from_srgb_to_scene_linear() method on
    # the Color class, but for this we would need to construct a Color instance
    # in the first place, and this is probably overkill.
    r, g, b, a = color
    return (r**2.2, g**2.2, b**2.2, a)


def find_image_by_name(name: str) -> Image | None:
    """Searches for an image in bpy.data.images by its name.

    Args:
        name: The name of the image to find.

    Returns:
        the image object, or None if not found.
    """
    for img in bpy.data.images:
        if img.name == name:
            return img


def get_pixel(image: Image, x: int, y: int) -> RGBAColor:
    """Gets the color of a given pixel of an image.

    Note that this function is very slow, if possible, use the
    `image.pixels.foreach_get()` function instead.

    The returned color is in sRGB space. Convert it to linear space if needed
    with the `convert_from_srgb_to_linear()` function.
    """
    width = image.size[0]
    offs = (x + y * width) * 4

    return image.pixels[offs : offs + 4]  # type: ignore
