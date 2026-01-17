from typing import Optional

import bpy
from bpy.types import Material

from sbstudio.model.types import RGBAColor

from .errors import SkybrushStudioAddonError

__all__ = (
    "create_colored_material",
    "create_glowing_material",
    "get_material_for_led_light_color",
    "get_material_for_pyro",
    "set_emission_strength_of_material",
)

is_blender_6_or_later = bpy.app.version >= (6, 0, 0)


def _create_material(name: str):
    """Creates a new, general purpose material with the given name."""
    mat = bpy.data.materials.new(name)

    # use_nodes will be removed in Blender 6
    if not is_blender_6_or_later:
        mat.use_nodes = True

    return mat


def _find_shader_node_by_name_and_type(material, name: str, type: str):
    """Finds the first shader node with the given name and expected type in the
    shader node tree of the given material.

    Lookup by name will likely fail if Blender is localized; in this case we
    will return the _first_ shader node that matches the given type.

    Parameters:
        name: the name of the shader node
        type: the expected type of the shader node

    Raises:
        KeyError: if there is no such shader node in the material
    """
    nodes = material.node_tree.nodes

    try:
        node = nodes[name]
        if node.type == type:
            return node
    except KeyError:
        pass

    # Lookup by name failed, let's try the slower way
    for node in nodes:
        if node.type == type:
            return node

    raise KeyError(f"no shader node with type {type!r} in material")


def create_colored_material(name: str, color: RGBAColor):
    """Creates a single-color material.

    Parameters:
        name: name of the material to create
        color: color of the material as an RGBA tuple

    Returns:
        object: the material that was created
    """
    mat = _create_material(name)
    _set_diffuse_color_of_material(mat, color)
    _set_specular_reflection_intensity_of_material(mat, 0)
    return mat


def create_glowing_material(
    name: str, color: RGBAColor = (1.0, 1.0, 1.0, 1.0), strength: float = 1.0
):
    """Creates a single-color glowing material.

    Parameters:
        name: name of the material to create
        color: color of the material as an RGBA tuple
        strength: the strength of the light emission shader

    Returns:
        object: the material that was created
    """
    mat = _create_material(name)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    links.clear()
    nodes.clear()

    object_info_node = nodes.new("ShaderNodeObjectInfo")
    object_info_node.location = (-300, 0)

    emission_node = nodes.new("ShaderNodeEmission")
    emission_node.inputs["Strength"].default_value = strength
    emission_node.location = (0, 0)

    output_node = nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (300, 0)

    links.new(object_info_node.outputs["Color"], emission_node.inputs["Color"])
    links.new(emission_node.outputs["Emission"], output_node.inputs["Surface"])

    _set_diffuse_color_of_material(mat, color)

    return mat


def get_material_for_led_light_color(drone) -> Optional[Material]:
    """Returns the material of the given drone object that is supposed to
    correspond to the LED light.

    Returns:
        the material of the LED light or `None` if no such material has been
            set up on the drone yet
    """
    if len(drone.material_slots) > 0:
        return drone.material_slots[0].material
    else:
        return None


def get_material_for_pyro(drone) -> Optional[Material]:
    """Returns the material of the given drone object that is supposed to
    correspond to the pyro.

    Args:
        drone: the drone object to get the material from

    Returns:
        the material of the pyro or `None` if no such material has been
            set up on the drone yet
    """
    if len(drone.material_slots) > 1:
        return drone.material_slots[1].material
    else:
        return None


def _set_diffuse_color_of_material(material, color: RGBAColor):
    """Sets the diffuse color of the given material to the given value.

    The material must use a principled BSDF or an emission shader.

    Parameters:
        material: the Blender material to update
        color: the color to apply to the material
    """
    if material.use_nodes:
        # Material is using shader nodes so we need to adjust the diffuse
        # color in the shader as well (the base property would control only
        # what we see in the preview window)
        _, input = _get_shader_node_and_input_for_diffuse_color_of_material(material)
        input.default_value = color

    material.diffuse_color = color


def set_emission_strength_of_material(material, value: float) -> None:
    """Updates the strength of the emission node of the material if it has one."""
    if not material.use_nodes:
        return

    try:
        node = _find_shader_node_by_name_and_type(material, "Emission", "EMISSION")
        input = node.inputs["Strength"]
    except KeyError:
        return

    input.default_value = value


def _get_shader_node_and_input_for_diffuse_color_of_material(material):
    """Returns a reference to the shader node and its input that controls the
    diffuse color of the given material.

    The material must use a principled BSDF or an emission shader.

    Parameters:
        material: the Blender material to update

    Raises:
        SkybrushStudioAddonError: if the material does not use shader nodes
    """
    try:
        node = _find_shader_node_by_name_and_type(material, "Emission", "EMISSION")
        input = node.inputs["Color"]
        return node, input
    except KeyError:
        try:
            node = _find_shader_node_by_name_and_type(
                material, "Principled BSDF", "BSDF_PRINCIPLED"
            )
            input = node.inputs["Base Color"]
            return node, input
        except KeyError:
            try:
                node = _find_shader_node_by_name_and_type(
                    material, "Principled BSDF", "BSDF_PRINCIPLED"
                )
                input = node.inputs["Emission Color"]
                return node, input
            except KeyError:
                raise SkybrushStudioAddonError(
                    "Material does not have a diffuse color shader node"
                ) from None


def _set_specular_reflection_intensity_of_material(material, intensity):
    """Sets the intensity of the specular reflection of the material.

    The material must use a principled BSDF shader.

    Parameters:
        material: the Blender material to update
        intensity: the specular reflection intensity
    """
    material.specular_intensity = intensity
    node = _find_shader_node_by_name_and_type(
        material, "Principled BSDF", "BSDF_PRINCIPLED"
    )
    node.inputs["Specular IOR Level"].default_value = intensity
