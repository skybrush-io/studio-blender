import bpy

from sbstudio.model.types import RGBAColor

__all__ = (
    "add_light_emission_to_material",
    "create_colored_material",
    "create_glowing_material",
    "set_diffuse_color_of_material",
    "set_specular_reflection_intensity_of_material",
)


def add_light_emission_to_material(material, emit=0.0):
    """Modifies the given material such that it emits light on its own.

    Parameters:
        emit (float): amount of light to emit
    """
    if False and material.use_nodes:
        material.node_tree.nodes["Principled BSDF"].inputs["Emission"].default_value = (
            emit * 10
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


def set_diffuse_color_of_material(material, color):
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
        nodes = material.node_tree.nodes
        try:
            nodes["Emission"].inputs["Color"].default_value = color
        except KeyError:
            nodes["Principled BSDF"].inputs["Base Color"].default_value = color
    material.diffuse_color = color


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
