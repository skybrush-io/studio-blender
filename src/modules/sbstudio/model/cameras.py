"""Module containing classes representing cameras."""

from __future__ import annotations

from dataclasses import dataclass

from sbstudio.model.types import Coordinate3D, Quaternion

__all__ = ("Camera",)


@dataclass
class Camera:
    """Class representing a single camera in the scene.

    This class is a simplified representation of the properties that a
    typical camera may have in a real 3D software like Blender.
    """

    name: str
    """The name of the camera."""

    position: Coordinate3D
    """The position of the camera in 3D space."""

    orientation: Quaternion
    """The orientation of the camera using Blender quaternions."""

    def as_dict(self, ndigits: int = 3):
        """Returns the camera as a dictionary.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary representation of the camera, rounded to
                the desired precision
        """
        result = {
            "name": self.name,
            "type": "perspective",
            "position": [round(value, ndigits=ndigits) for value in self.position],
            "orientation": [
                round(value, ndigits=ndigits) for value in self.orientation
            ],
        }

        return result
