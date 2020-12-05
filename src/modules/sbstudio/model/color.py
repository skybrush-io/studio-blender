from dataclasses import dataclass

__all__ = ("Color4D",)


@dataclass
class Color4D:
    """Simplest representation of a 4D color in RGB space and time."""

    #: time in [s]
    t: float

    #: red component of the color in the range [0-255]
    r: int

    #: green component of the color in the range[0-255]
    g: int

    #: blue component of the color in the range[0-255]
    b: int

    #: flag to specify whether we should fade here from the previous keypoint
    #: (True) or maintain previous color until this moment and change here
    #: abruptly (False)
    is_fade: bool = True
