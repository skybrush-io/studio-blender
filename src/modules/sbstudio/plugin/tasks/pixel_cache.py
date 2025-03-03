from sbstudio.plugin.model.light_effects import invalidate_pixel_cache
from sbstudio.plugin.tasks.base import Task

__all__ = ("InvalidatePixelCacheTask",)


def invalidate_light_effect_pixel_cache(*args):
    # Used to ignore the positional arguments
    invalidate_pixel_cache(static=True, dynamic=True)


def invalidate_light_effect_pixel_cache_for_dynamic_images(*args):
    invalidate_pixel_cache(static=False, dynamic=True)


class InvalidatePixelCacheTask(Task):
    """Background task that is invoked after every frame change and that is
    responsible for invalidating cached pixel-level representations of light
    effect images.
    """

    functions = {
        "depsgraph_update_post": invalidate_light_effect_pixel_cache_for_dynamic_images,
        "frame_change_post": invalidate_light_effect_pixel_cache_for_dynamic_images,
        "load_post": invalidate_light_effect_pixel_cache,
    }
