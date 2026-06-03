from .light_fx import register as register_light_fx_presets
from .light_fx import unregister as unregister_light_fx_presets

__all__ = (
    "register",
    "unregister",
)


def register():
    """Register translations for the built-in presets.

    Called by the addon's top-level ``register()`` function.  Idempotent.
    """
    register_light_fx_presets()


def unregister():
    unregister_light_fx_presets()
