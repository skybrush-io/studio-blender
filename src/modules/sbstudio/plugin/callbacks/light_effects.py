"""Callback functionality related to light effects."""

from typing import Protocol, Sequence

from bpy.types import Object

from sbstudio.model.types import RGBAColor

from .base import CallbackList

__all__ = ("LightEffectColorUpdateCallback", "final_color_updated_callbacks")


class LightEffectColorUpdateCallback(Protocol):
    def __call__(
        self,
        drones: Sequence[Object],
        colors: Sequence[RGBAColor],
        has_active_effects: bool,
    ) -> None:
        """Type of callback function used to get notifications about the color update
        of drones as a result of their light effect evaluation. The first parameter
        defines the list of drones, the second the list of final colors and the third
        whether there are active light effects at the moment.
        """
        ...


final_color_updated_callbacks: CallbackList[
    [Sequence[Object], Sequence[RGBAColor], bool]
] = CallbackList()
