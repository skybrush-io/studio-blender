"""Background task that is called every time a new file is loaded, and that
turns on the bloom effect on the scene if needed.
"""

from sbstudio.plugin.utils.bloom import enable_bloom_effect_if_needed

from .base import Task


def update_bloom_effect(*args):
    enable_bloom_effect_if_needed()


class InitializationTask(Task):
    """Background task that is called every time a new file is loaded, and that
    turns on the bloom effect on the scene if needed.
    """

    functions = {
        "load_post": update_bloom_effect,
    }
