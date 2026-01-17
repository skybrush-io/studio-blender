from random import randint

import bpy
from bpy.types import Object, ParticleSystem

from sbstudio.model.pyro_markers import PyroMarker, PyroMarkers
from sbstudio.plugin.constants import NUM_PYRO_CHANNELS
from sbstudio.plugin.materials import get_material_for_pyro
from sbstudio.plugin.operators.detach_materials_from_template import (
    detach_pyro_material_from_drone_template,
)

__all__ = (
    "add_pyro_marker_to_object",
    "ensure_pyro_particle_system",
    "get_pyro_markers_of_object",
    "remove_pyro_particle_system",
    "set_pyro_markers_of_object",
    "update_pyro_particles_of_object",
)


def add_pyro_marker_to_object(ob: Object, channel: int, marker: PyroMarker) -> None:
    """Add a pyro marker to the Skybrush context of an object.

    Args:
        object: the object to add the new pyro marker to
        channel: the pyro channel to add the trigger event to
        marker: the marker to add
    """
    markers = get_pyro_markers_of_object(ob)
    markers.markers[int(channel)] = marker
    set_pyro_markers_of_object(ob, markers)


def get_pyro_markers_of_object(ob: Object) -> PyroMarkers:
    """Get pyro markers from the Skybrush context of an object.

    Args:
        object: the object to get pyro markers from

    Returns:
        pyro markers
    """

    # TODO: add error handling in case string representation is bad

    return PyroMarkers.from_str(ob.skybrush.pyro_markers)


def ensure_pyro_particle_system(ob: Object, channel: int) -> ParticleSystem:
    """Returns the particle system associated with a given
    object and pyro channel. If it is not existing yet,
    create it first.

    Args:
        ob: the object of the pyro particle system
        channel: the 1-based pyro channel to use

    Returns:
        the particle system associated with the given object
            and pyro channel
    """
    # ensure material
    if get_material_for_pyro(ob) is None:
        detach_pyro_material_from_drone_template(ob)

    # ensure particle system
    key = f"pyro_{channel}"
    particle_system = next((ps for ps in ob.particle_systems if ps.name == key), None)
    if particle_system is None:
        particle_settings = bpy.data.particles.new(name=f"{key}_settings")
        ob.modifiers.new(name=key, type="PARTICLE_SYSTEM")
        particle_system = ob.particle_systems[-1]
        particle_system.settings = particle_settings
        particle_settings.material = 2

    return particle_system


def remove_pyro_particle_system(ob: Object, channel: int) -> None:
    """Removes the particle system associated with a given
    object and pyro channel if it is existing.

    Args:
        ob: the object of the pyro particle system
        channel: the 1-based pyro channel to use

    """
    # ensure material
    if get_material_for_pyro(ob) is None:
        return

    # ensure particle system
    key = f"pyro_{channel}"
    particle_system = next((ps for ps in ob.particle_systems if ps.name == key), None)
    modifier = next((ps for ps in ob.modifiers if ps.name == key), None)
    if particle_system is not None:
        particle_settings = particle_system.settings
        ob.modifiers.remove(modifier)
        # if particle_settings.users == 0:
        bpy.data.particles.remove(particle_settings)


def set_pyro_markers_of_object(ob: Object, markers: PyroMarkers) -> None:
    """Set pyro markers of an object in its Skybrush context.

    Args:
        object: the object to set pyro markers of
        markers: the markers to set
    """
    ob.skybrush.pyro_markers = markers.as_str()

    update_pyro_particles_of_object(ob)


def update_pyro_particles_of_object(ob: Object) -> None:
    """Set or clear pyro particle systems based on pyro markers
    and global pyro visualization type.

    Args:
        ob: the object to update pyro particles on
    """
    pyro_control = bpy.context.scene.skybrush.pyro_control
    enable = pyro_control.visualization == "PARTICLES"
    markers = get_pyro_markers_of_object(ob)
    for i in range(1, NUM_PYRO_CHANNELS + 1):
        # add pyro particle system
        if enable and i in markers.markers.keys():
            particle_system = ensure_pyro_particle_system(ob, i)
            particle_settings = particle_system.settings
            marker = markers.markers[i]
            fps = bpy.context.scene.render.fps
            particle_system.seed = randint(0, 10000)
            particle_settings.type = "EMITTER"
            particle_settings.count = int(
                marker.payload.duration * 50
            )  # 50 particles/sec
            particle_settings.frame_start = marker.frame
            particle_settings.frame_end = (
                marker.frame + (marker.payload.duration + randint(-4, 4)) * fps
            )
            particle_settings.lifetime = randint(1 * fps, 2 * fps)
            particle_settings.emit_from = "VERT"
            particle_settings.use_emit_random = True
            particle_settings.brownian_factor = 4
            particle_settings.render_type = "HALO"
        # remove pyro partical system
        else:
            remove_pyro_particle_system(ob, i)
