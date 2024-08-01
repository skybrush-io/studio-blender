from typing import Literal

def blend_set(
    mode: Literal[
        "NONE",
        "ALPHA",
        "ALPHA_PREMULT",
        "ADDITIVE",
        "ADDITIVE_PREMULT",
        "MULTIPLY",
        "SUBTRACT",
        "INVERT",
    ],
) -> None: ...
def line_width_set(size: float) -> None: ...
def point_size_set(size: float) -> None: ...
