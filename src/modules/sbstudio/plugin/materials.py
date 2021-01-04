import bpy

from bpy.types import Material
from typing import Optional

from sbstudio.model.types import RGBAColor

from .errors import SkybrushStudioAddonError

__all__ = (
    "create_colored_material",
    "create_glowing_material",
    "get_shader_node_and_input_for_diffuse_color_of_material",
    "set_diffuse_color_of_material",
    "set_led_light_color",
    "set_specular_reflection_intensity_of_material",
)


def _create_material(name: str):
    """Creates a new, general purpose material with the given name."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    return mat


def create_colored_material(name: str, color: RGBAColor):
    """Creates a single-color material.

    Parameters:
        name: name of the material to create
        color: color of the material as an RGBA tuple

    Returns:
        object: the material that was created
    """
    mat = _create_material(name)
    set_diffuse_color_of_material(mat, color)
    set_specular_reflection_intensity_of_material(mat, 0)
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

    emission_node = nodes.new("ShaderNodeEmission")
    emission_node.inputs["Strength"].default_value = strength

    output_node = nodes.new("ShaderNodeOutputMaterial")

    links.new(emission_node.outputs["Emission"], output_node.inputs["Surface"])

    set_diffuse_color_of_material(mat, color)

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


def get_diffuse_color_of_material(material) -> RGBAColor:
    """Returns the diffuse color of the given material to the given value.

    The material must use a principled BSDF or an emission shader.

    Parameters:
        material: the Blender material to update
        color: the color to apply to the material
    """
    if material.use_nodes:
        # Material is using shader nodes so we need to adjust the diffuse
        # color in the shader as well (the base property would control only
        # what we see in the preview window)
        _, input = get_shader_node_and_input_for_diffuse_color_of_material(material)
        return tuple(input.default_value)
    else:
        return material.diffuse_color


def set_diffuse_color_of_material(material, color: RGBAColor):
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
        _, input = get_shader_node_and_input_for_diffuse_color_of_material(material)
        input.default_value = color

    material.diffuse_color = color


def get_led_light_color(drone) -> RGBAColor:
    """Returns the color of the LED light on the given drone.

    Parameters:
        drone: the drone to query
        color: the color to apply to the LED light of the drone
    """
    material = get_material_for_led_light_color(drone)
    if material is not None:
        return get_diffuse_color_of_material(material)
    else:
        return (0.0, 0.0, 0.0, 0.0)


def set_led_light_color(drone, color: RGBAColor):
    """Sets the color of the LED light on the given drone.

    Parameters:
        drone: the drone to update
        color: the color to apply to the LED light of the drone
    """
    material = get_material_for_led_light_color(drone)
    if material is not None:
        set_diffuse_color_of_material(material, color)


def get_shader_node_and_input_for_diffuse_color_of_material(material):
    """Returns a reference to the shader node and its input that controls the
    diffuse color of the given material.

    The material must use a principled BSDF or an emission shader.

    Parameters:
        material: the Blender material to update

    Raises:
        SkybrushStudioAddonError: if the material does not use shader nodes
    """
    nodes = material.node_tree.nodes
    try:
        node = nodes["Emission"]
        input = node.inputs["Color"]
        return node, input
    except KeyError:
        try:
            node = nodes["Principled BSDF"]
            input = node.inputs["Base Color"]
            return node, input
        except KeyError:
            raise SkybrushStudioAddonError(
                "Material does not have a diffuse color shader node"
            )


def set_specular_reflection_intensity_of_material(material, intensity):
    """Sets the intensity of the specular reflection of the material.

    The material must use a principled BSDF shader.

    Parameters:
        material: the Blender material to update
        intensity: the specular reflection intensity
    """
    material.specular_intensity = intensity
    nodes = material.node_tree.nodes
    nodes["Principled BSDF"].inputs["Specular"].default_value = intensity
