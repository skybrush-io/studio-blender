"""Background task that is called every time a new file is loaded."""

import bpy

from random import randint

from sbstudio.plugin.constants import Collections, RANDOM_SEED_MAX
from sbstudio.plugin.utils.bloom import enable_bloom_effect_if_needed
from sbstudio.plugin.utils.pyro_markers import update_pyro_particles_of_object

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


def remove_legacy_formation_constraints(*args):
    """Removes legacy formation constraints from the file that were created
    before we have migrated to formation constraints that refer a unique ID of
    a storyboard entry instead of simply referring to a formation.
    """
    drones = Collections.find_drones(create=False)
    if not drones:
        return

    to_delete = []
    for drone in drones.objects:
        to_delete.clear()

        for constraint in drone.constraints:
            if constraint.type == "COPY_LOCATION" and "[To " in constraint.name:
                to_delete.append(constraint)

        if to_delete:
            for constraint in reversed(to_delete):
                drone.constraints.remove(constraint)


def setup_random_seed(*args):
    """Sets up a unique random seed for the file if it does not have one."""

    # Legacy files that were created before the random seed property was added
    # will be loaded with a seed of zero (this is the default value of the
    # property), and we use that to detect that a seed has not been set up yet.
    scene = bpy.context.scene
    if scene and scene.skybrush.settings.random_seed == 0:
        scene.skybrush.settings.random_seed = randint(1, RANDOM_SEED_MAX)


def update_bloom_effect(*args):
    enable_bloom_effect_if_needed()


def update_pyro_particles_of_drones(*args):
    """Updates the pyro particles of drones."""
    drones = Collections.find_drones(create=False)
    if not drones:
        return

    for drone in drones.objects:
        update_pyro_particles_of_object(drone)


def config_logging(*args):
    import logging

    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        level=logging.INFO,
        datefmt="%H:%M:%S",
    )


class InitializationTask(Task):
    """Background task that is called every time a new file is loaded."""

    functions = {
        "load_post": [
            update_bloom_effect,
            setup_drone_collection,
            remove_legacy_formation_constraints,
            setup_random_seed,
            update_pyro_particles_of_drones,
            config_logging,
        ]
    }
