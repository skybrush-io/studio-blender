"""Utility functions related to Blender images."""

from dataclasses import dataclass

import bpy
from bpy.types import Image
from numpy import array, empty, float32, pow
from numpy.typing import NDArray

from sbstudio.model.types import RGBAColor

__all__ = [
    "convert_from_srgb_to_linear",
    "convert_pixels_from_srgb_to_linear",
    "convert_pixels_to_linear_in_place",
    "find_image_by_name",
    "get_pixel",
    "PixelsWithColorspace",
]


_colorspaces_warned: set[str] = set()


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


_SRGB_TO_LINEAR_EXPONENTS = array([2.2, 2.2, 2.2, 1.0], dtype=float32)


def convert_pixels_to_linear_in_place(colors: NDArray[float32], colorspace: str) -> str:
    """Converts a color from sRGB to linear space, vectorized variant.

    Args:
        color: The colors to convert, one color per row, in a NumPy array.
        colorspace: The color space of the pixels.

    Returns:
        the new color space; either `Linear Rec.709` or the original color space if no
        conversion was done.
    """
    match colorspace:
        case "":
            pass  # no color management
        case "Linear Rec.709":
            pass  # nothing to do, already linear
        case "sRGB":
            convert_pixels_from_srgb_to_linear(colors, out=colors)
            return "Linear Rec.709"
        case _:
            if colorspace not in _colorspaces_warned:
                _colorspaces_warned.add(colorspace)
                print(
                    f"Warning: Cannot convert unsupported color space {colorspace!r} to linear."
                )

    return colorspace


def convert_pixels_from_srgb_to_linear(
    colors: NDArray[float32], *, out: NDArray[float32] | None = None
) -> NDArray[float32]:
    """Converts a color from sRGB to linear space, vectorized variant.

    Args:
        color: The colors to convert, one color per row, in a NumPy array.
        out: Destination array to write the result to; `None` to create a new array.

    Returns:
        the destination array
    """
    # This is an approximation, not the standard one. We can live with it for the
    # time being as the differences are mostly in the low intensities and drone LEDs
    # are not able to reproduce those anyways.
    return pow(colors, _SRGB_TO_LINEAR_EXPONENTS, out=out)


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


@dataclass
class PixelsWithColorspace:
    """Simple data object for associating raw pixel data of an image with the color
    space that the pixels are in.
    """

    pixels: NDArray[float32]
    """The raw pixel data of an image, in the form of a NumPy array with shape
    (height, width, 4) and dtype float32.
    """

    colorspace: str = ""
    """The color space of the pixels, as a string. An empty string indicates that
    the pixels are to be treated as data and should not be color-managed.
    """

    @classmethod
    def from_image(cls, image: Image) -> "PixelsWithColorspace":
        """Creates a PixelsWithColorspace object from a Blender image.

        Args:
            image: The Blender image to create the object from
        """
        pixel_data = image.pixels
        pixels: NDArray[float32] = empty(len(pixel_data), dtype=float32)
        pixel_data.foreach_get(pixels)
        pixels = pixels.reshape(tuple(image.size) + (-1,))

        colorspace_settings = image.colorspace_settings
        colorspace = colorspace_settings.name if not colorspace_settings.is_data else ""

        return cls(pixels, colorspace)

    def to_linear(self) -> None:
        """Converts the pixels from its native color space to linear space."""
        self.colorspace = convert_pixels_to_linear_in_place(
            self.pixels, self.colorspace
        )
