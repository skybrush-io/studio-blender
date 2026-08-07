"""Module containing classes representing terrain."""

from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass

from sbstudio.model.types import Coordinate3D, Quaternion

__all__ = ("Terrain",)


@dataclass
class Terrain:
    """Class representing a terrain in the scene."""

    file_path: str
    """The full path pointing to the (.glb) terrain file."""

    position: Coordinate3D = (0, 0, 0)
    """The position of the terrain in 3D space."""

    rotation: Quaternion = (1, 0, 0, 0)
    """The rotation of the terrain using Blender quaternions."""

    scale: Coordinate3D = (1, 1, 1)
    """The scaling factors of the terrain along the 3 axes of the 3D space."""

    def as_dict(self, ndigits: int = 3):
        """Returns the terrain as a dictionary.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary representation of the terrain, rounded to
                the desired precision
        """
        with open(self.file_path, "rb") as fp:
            data = b64encode(fp.read()).decode("ascii")

        result = {
            "model": {
                "data": data,
                "mediaType": "model/gltf-binary",
            },
            "transform": {
                "position": [round(value, ndigits=ndigits) for value in self.position],
                "rotation": [round(value, ndigits=ndigits) for value in self.rotation],
                "scale": [round(value, ndigits=ndigits) for value in self.scale],
            },
        }

        return result
