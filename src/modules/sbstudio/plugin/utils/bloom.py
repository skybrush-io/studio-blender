"""Functions to enable or disable a bloom effect on the 3D view."""

import bpy

from sbstudio.plugin.constants import Collections, Templates
from sbstudio.plugin.materials import (
    get_material_for_led_light_color,
    set_emission_strength_of_material,
)
from sbstudio.plugin.views import find_all_3d_views

__all__ = (
    "disable_bloom_effect",
    "enable_bloom_effect",
    "set_bloom_effect_enabled",
    "update_emission_strength",
)


def enable_bloom_effect() -> None:
    """Enables the bloom effect on the 3D view."""
    set_bloom_effect_enabled(True)


def enable_bloom_effect_if_needed() -> None:
    """Enables the bloom effect on the 3D view if the "Drones" collection
    exists. Used to ensure that we do not add the bloom effect to ordinary
    Blender scenes.
    """
    if bpy.context.scene.skybrush.settings.use_bloom_effect:
        drones = Collections.find_drones(create=False)
        if drones:
            enable_bloom_effect()


def disable_bloom_effect() -> None:
    """Disables the bloom effect on the 3D view."""
    set_bloom_effect_enabled(False)


def set_bloom_effect_enabled(value: bool) -> None:
    """Enables or disables the bloom effect on the 3D view."""
    if value:
        bpy.context.scene.eevee.use_bloom = True
        bpy.context.scene.eevee.bloom_radius = 4
        bpy.context.scene.eevee.bloom_intensity = 0.2
        for space in find_all_3d_views():
            space.shading.type = "MATERIAL"

    else:
        bpy.context.scene.eevee.use_bloom = False


def update_emission_strength(value: float) -> None:
    """Updates the strength of the emission shader node on the materials of
    all the drones.
    """
    drones = Collections.find_drones().objects
    for drone in drones:
        material = get_material_for_led_light_color(drone)
        set_emission_strength_of_material(material, value)

    template = Templates.find_drone()
    if template:
        material = get_material_for_led_light_color(template)
        set_emission_strength_of_material(material, value)
