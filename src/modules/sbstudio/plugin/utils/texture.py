"""Utility functions related to Blender textures."""

import bpy

from bpy.types import Texture, ImageTexture

from typing import Any

from sbstudio.plugin.utils.color_ramp import (
    color_ramp_as_dict,
    update_color_ramp_from_dict,
)
from sbstudio.plugin.utils.image import find_image_by_name


__all__ = (
    "texture_as_dict",
    "update_texture_from_dict",
)


def texture_as_dict(source: Texture) -> dict[str, Any]:
    """Returns a dictionary representation of a texture.

    Parameters:
        source: the source texture to export

    Returns:
        a dictionary representation of the source texture
    """
    retval = {
        "colorRamp": None,
        "useColorRamp": source.use_color_ramp,
        "imageName": None,
    }

    if isinstance(source, ImageTexture) and source.image is not None:
        # Note that we do _not_ store the whole image, only its name reference;
        # users must have the same image in bpy.data.images to be able to
        # load it back later on
        retval["imageName"] = source.image.name
    if source.color_ramp is not None:
        retval["colorRamp"] = color_ramp_as_dict(source.color_ramp)

    return retval


def update_texture_from_dict(target: ImageTexture, data: dict[str, Any]) -> None:
    """Updates a texture from its dictionary representation.

    Parameters:
        target: the texture to update
        data: the dictionary representation of a texture as the data source
    """
    if use_color_ramp := data.get("useColorRamp"):
        target.use_color_ramp = use_color_ramp

    if color_ramp := data.get("colorRamp"):
        update_color_ramp_from_dict(target.color_ramp, color_ramp)

    if image_name := data.get("imageName"):
        if image := find_image_by_name(image_name):
            target.image = image
        else:
            print(
                f"WARNING: could not import texture: image {image_name!r} is not part of bpy.data.images"
            )

        # TODO: setup properly in light effect
