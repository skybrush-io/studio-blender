"""Background task that is invoked after every frame change and that is
responsible for updating the colors of the drones according to the active
light effects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import bpy
from bpy.types import Object

from sbstudio.model.types import RGBAColor
from sbstudio.plugin.callbacks import final_color_updated_callbacks
from sbstudio.plugin.tasks.base import Task
from sbstudio.plugin.tasks.utils import Suspension
from sbstudio.plugin.views import redraw_all_3d_views

from .updater import LightEffectUpdater

if TYPE_CHECKING:
    from bpy.types import Depsgraph, Object, Scene

__all__ = (
    "UpdateLightEffectsTask",
    "get_base_color_of_drone",
    "get_final_color_of_drone",
    "suspended_color_update_callbacks",
    "suspended_light_effects",
)


light_effect_suspension = Suspension()
"""Object to manage the suspension logic for the light effect task."""

color_update_callbacks_suspension = Suspension()
"""Object to manage the suspension logic for color update callbacks."""


_light_effect_updater: LightEffectUpdater = LightEffectUpdater()
"""Single instance of the light effect updater process."""


@light_effect_suspension.wrap
def update_light_effects(scene: Scene, depsgraph: Depsgraph):
    updates = _light_effect_updater.update(scene)
    if not color_update_callbacks_suspension.active:
        final_color_updated_callbacks(updates)


def get_base_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) base color of the drone at the current frame
    before any active light effects are applied on it."""
    return _light_effect_updater.get_base_color_of_drone(drone)


def get_final_color_of_drone(drone: Object) -> RGBAColor:
    """Returns the (cached) final color of the drone at the current frame
    after all active light effects are applied on it."""
    return _light_effect_updater.get_final_color_of_drone(drone)


suspended_light_effects = light_effect_suspension.use
"""Context manager that suspends the calculation of light effects when the
context is entered and re-enables them when the context is exited.

Useful when sampling only the positions of the drones (or any other information that
does not require the evaluation of light effects). Implies the suspension of color
update callbacks as well since the colors are not going to be updated.
"""

suspended_color_update_callbacks = color_update_callbacks_suspension.use
"""Context manager that suspends the execution of color update callbacks when
the context is entered and re-enables them when the context is exited. Light
effects are still calculated and cached.

Useful when sampling the LED colors of the drones in a manner that does not require the
3D viewport to be updated.
"""


def _update_light_effects_post_load(*args):
    context = bpy.context
    update_light_effects(context.scene, context.evaluated_depsgraph_get())
    redraw_all_3d_views()


class UpdateLightEffectsTask(Task):
    """Background task that is invoked after every frame change and that is
    responsible for updating the colors of the drones according to the active
    light effects.
    """

    functions = {
        "depsgraph_update_post": update_light_effects,
        "frame_change_post": update_light_effects,
        "load_post": _update_light_effects_post_load,
    }
