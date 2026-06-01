"""Callback functionality related to light effects."""

from collections.abc import Callable, Iterator

from bpy.types import Object

from sbstudio.model.types import RGBAColor

__all__ = (
    "LightEffectColorUpdateCallback",
    "get_final_color_update_callbacks",
    "register_final_color_update_callback",
    "unregister_final_color_update_callback",
)


LightEffectColorUpdateCallback = Callable[
    [list[Object], list[RGBAColor], bool],
    None,
]
"""Type of callback function used to get notifications about the color update
of drones as a result of their light effect evaluation. The first parameter
defines the list of drones, the second the list of final colors and the third
whether there are active light effects at all currently."""


_final_color_update_callbacks: list[LightEffectColorUpdateCallback] = []
"""Callback functions registered to get notification about light effect
color updates."""


def get_final_color_update_callbacks() -> Iterator[LightEffectColorUpdateCallback]:
    for cb in _final_color_update_callbacks:
        yield cb


def register_final_color_update_callback(
    callback: LightEffectColorUpdateCallback,
) -> None:
    if callback not in _final_color_update_callbacks:
        _final_color_update_callbacks.append(callback)


def unregister_final_color_update_callback(
    callback: LightEffectColorUpdateCallback,
) -> None:
    if callback in _final_color_update_callbacks:
        _final_color_update_callbacks.remove(callback)
