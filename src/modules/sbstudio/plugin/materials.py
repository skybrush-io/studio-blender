import bpy

from bpy.types import Material
from typing import Optional, Tuple, Union

from sbstudio.model.types import RGBAColor, RGBAColorLike
from sbstudio.plugin.actions import ensure_action_exists_for_object
from sbstudio.plugin.keyframes import set_keyframes

from .errors import SkybrushStudioAddonError

__all__ = (
    "create_colored_material",
    "create_glowing_material",
    "get_shader_node_and_input_for_diffuse_color_of_material",
    "set_diffuse_color_of_material",
    "set_led_light_color",
    "set_specular_reflection_intensity_of_material",
)

is_blender_4 = bpy.app.version >= (4, 0, 0)


def _create_material(name: str):
    """Creates a new, general purpose material with the given name."""
    mat = bpy.data.materials.new(name)
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


def create_keyframe_for_diffuse_color_of_material(
    material,
    color: Union[
        Tuple[float, float, float], Tuple[float, float, float, float], RGBAColor
    ],
    *,
    frame: Optional[int] = None,
    step: bool = False,
):
    """Creates keyframes for the diffuse color of the given material to set it
    to the given color in the given frame.

    Parameters:
        material: the material to modify
        color: the RGB color to use for the diffuse color of the material
        frame: the frame to apply the diffuse color on; `None` means the
            current frame
        step: whether to insert an additional keyframe in the preceding frame to
            ensure an abrupt transition
    """
    if frame is None:
        frame = bpy.context.scene.frame_current

    # Ensure that we have animation data for the shader node tree. we need
    # to use a custom name because all the node trees otherwise have the
    # same name ("Shader Nodetree") so they would get the same action
    node_tree = material.node_tree
    ensure_action_exists_for_object(
        node_tree, name=f"{material.name} Shader Nodetree Action"
    )

    if hasattr(color, "r"):
        color_as_rgba = color.r, color.g, color.b, 1.0
    else:
        color_as_rgba = color[0], color[1], color[2], 1.0

    keyframes = [(frame, color_as_rgba)]
    if step and frame > bpy.context.scene.frame_start:
        keyframes.insert(0, (frame - 1, None))

    # Set the keyframes
    node, input = get_shader_node_and_input_for_diffuse_color_of_material(material)
    index = node.inputs.find(input.name)
    data_path = f'nodes["{node.name}"].inputs[{index}].default_value'
    set_keyframes(node_tree, data_path, keyframes, interpolation="LINEAR")


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


def set_led_light_color(drone, color: RGBAColorLike):
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
                input = node.inputs["Emission Color" if is_blender_4 else "Emission"]
                return node, input
            except KeyError:
                raise SkybrushStudioAddonError(
                    "Material does not have a diffuse color shader node"
                ) from None


def set_specular_reflection_intensity_of_material(material, intensity):
    """Sets the intensity of the specular reflection of the material.

    The material must use a principled BSDF shader.

    Parameters:
        material: the Blender material to update
        intensity: the specular reflection intensity
    """
    material.specular_intensity = intensity
    nodes = material.node_tree.nodes
    nodes["Principled BSDF"].inputs[
        "Specular IOR Level" if is_blender_4 else "Specular"
    ].default_value = intensity
