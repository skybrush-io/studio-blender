from .light_effects import register as register_light_effect_presets
from .light_effects import unregister as unregister_light_effect_presets

__all__ = (
    "register",
    "unregister",
)


def register():
    """Register translations for the built-in presets.

    Called by the addon's top-level ``register()`` function.  Idempotent.
    """
    register_light_effect_presets()


def unregister():
    unregister_light_effect_presets()
