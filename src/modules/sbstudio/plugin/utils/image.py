"""Utility functions related to Blender images."""


from sbstudio.model.types import RGBAColor


def get_pixel(image, x: int, y: int) -> RGBAColor:
    """Gets the color of a given pixel of an image.

    Note that this function is very slow, if possible,
    use the image.pixels.foreach_get() function instead.

    """
    width = image.size[0]
    offs = (x + y * width) * 4

    return image.pixels[offs : offs + 4]
