"""Callback functionality related to LED colors."""

from typing import Protocol

from sbstudio.plugin.model.light_effects import LightEffectUpdate

from .base import CallbackList

__all__ = ("LEDColorUpdateCallback", "final_color_updated_callbacks")


class LEDColorUpdateCallback(Protocol):
    def __call__(self, updates: LightEffectUpdate) -> None:
        """Type of callback function used to get notifications about the color update
        of drones as a result of their light effect evaluation.
        """
        ...


final_color_updated_callbacks: CallbackList[[LightEffectUpdate]] = CallbackList()
