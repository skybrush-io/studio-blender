"""Background task that is called every time a new file is loaded, and that
turns on the bloom effect on the scene if needed.
"""

import bpy

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.utils.bloom import enable_bloom_effect_if_needed

from .base import Task


def setup_drone_collection(*args):
    """Updates the `drone_collection` property of the file-specific settings
    to be equal to whatever `Collections.find_drones()` returns. Used to
    migrate old files where the `drone_collection` property did not exist yet
    but the user has already created a "Drones" collection.
    """
    drones = Collections.find_drones(create=False)
    scene = bpy.context.scene

    if drones and scene and scene.skybrush.settings.drone_collection is None:
        scene.skybrush.settings.drone_collection = drones


def update_bloom_effect(*args):
    enable_bloom_effect_if_needed()


class InitializationTask(Task):
    """Background task that is called every time a new file is loaded, and that
    turns on the bloom effect on the scene if needed.
    """

    functions = {"load_post": [update_bloom_effect, setup_drone_collection]}
