"""Built-in light effect output presets for Skybrush Studio.

Functions are referenced by a stable string ID, so projects stay portable
across machines and operating systems (no .py file paths inside .blend).

A preset function returns a float in ``[0, 1]`` for the X/Y axis of the
color ramp / image lookup, given:

    def my_preset(frame, time_fraction, drone_index, formation_index,
                  position, drone_count) -> float: ...

Display names follow the format ``<number><human-readable name>``,
e.g. ``「1」 Odd-Even Pulse`` (English) / ``①奇偶脉冲`` (Chinese). The number is
assigned by registration order across all categories.
"""

from __future__ import annotations

from .base import (
    get_preset_enum_items,
    get_preset_function,
    register_preset,
)
from .i18n import register, unregister

__all__ = (
    "get_preset_function",
    "get_preset_enum_items",
    "register_preset",
    "register",
    "unregister",
)

# Import light effect presets to register them and include them in the enum items list.
# Import order here decides the order in which they appear on the UI.
from ..light_effects import (
    basic,  # noqa: F401
    chasing_tails,  # noqa: F401
    filling,  # noqa: F401
    generic,  # noqa: F401
    groups,  # noqa: F401
    radar_scan,  # noqa: F401
    radial,  # noqa: F401
    sweep,  # noqa: F401
    wave,  # noqa: F401
)
