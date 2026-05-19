"""Module containing classes representing audio files."""

from base64 import b64encode
from dataclasses import dataclass

__all__ = ("Audio",)


@dataclass
class Audio:
    """Class representing a single audio file in the scene.

    This class is a simplified representation of the properties that a
    typical sound strips may have in a real 3D software like Blender.
    """

    file_path: str
    """The full path pointing to the audio file."""

    start_time: float
    """The start time of the audio strip relative to show start, in seconds."""

    def as_dict(self, ndigits: int = 3):
        """Returns the audio as a (JSON) dictionary.

        Parameters:
            ndigits: round floats to this precision

        Return:
            dictionary representation of the audio, rounded to
                the desired precision
        """
        with open(self.file_path, "rb") as fp:
            data = b64encode(fp.read()).decode("ascii")

        result = {
            "data": data,
            "mediaType": "audio/mpeg",
            "startTime": self.start_time,
        }

        return result
