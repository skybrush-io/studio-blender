import bpy
from bpy.types import Operator

from sbstudio.plugin.actions import ensure_action_exists_for_object
from sbstudio.plugin.constants import Collections, Templates
from sbstudio.plugin.errors import SkybrushStudioAddonError
from sbstudio.plugin.keyframes import get_keyframes, set_keyframes
from sbstudio.plugin.materials import (
    get_material_for_led_light_color,
    _get_shader_node_and_input_for_diffuse_color_of_material,
)

__all__ = ("UseSharedMaterialForAllDronesMigrationOperator",)


def add_object_info_to_shader_node_tree_of_drone_template() -> None:
    """Checks drone template and if it seems to be old, upgrade
    it to contain object info shader node as drone color source."""
    template = Templates.find_drone(create=False)
    template_material = get_material_for_led_light_color(template)
    if template_material is not None:
        _, input = _get_shader_node_and_input_for_diffuse_color_of_material(
            template_material
        )
        if not input.is_linked:
            nodes = template_material.node_tree.nodes
            links = template_material.node_tree.links
            object_info_node = nodes.new("ShaderNodeObjectInfo")
            links.new(object_info_node.outputs["Color"], input)
        elif input.links[0].from_node.name != "Object Info":
            raise SkybrushStudioAddonError("Template drone shader node tree mismatch")


def upgrade_drone_color_animations_and_drone_materials() -> None:
    """Moves drone color animation from shader nodes to object colors
    and replaces drone material with template material."""
    template = Templates.find_drone(create=False)
    template_material = get_material_for_led_light_color(template)
    drones = Collections.find_drones()
    for drone in drones.objects:
        material = get_material_for_led_light_color(drone)
        if material and material.name == f"LED color of {drone.name}":
            # copy color animation from shader node to drone
            node_tree = material.node_tree
            if node_tree.animation_data:
                node, input = _get_shader_node_and_input_for_diffuse_color_of_material(
                    material
                )
                index = node.inputs.find(input.name)
                data_path = f'nodes["{node.name}"].inputs[{index}].default_value'
                keyframes = get_keyframes(node_tree, data_path)
                ensure_action_exists_for_object(drone)
                set_keyframes(drone, "color", keyframes, interpolation="LINEAR")
            # reset drone's material to the template material
            drone.material_slots[0].material = template_material


def set_solid_shading_color_type_to_object() -> None:
    """Sets the object color source of the solid shading mode of the
    3D Viewport to use object color."""
    shading = bpy.context.space_data.shading
    shading.color_type = "OBJECT"
    shading.wireframe_color_type = "OBJECT"


class UseSharedMaterialForAllDronesMigrationOperator(Operator):
    """Upgrades old Blender file content (<=3.13.2) that uses
    a different material for all drone objects to store color animation to
    new version in which all drones share a common material.
    """

    bl_idname = "skybrush.use_shared_material_for_all_drones_migration"
    bl_label = "Use Shared Material For All Drones Migration"

    def execute(self, context):
        add_object_info_to_shader_node_tree_of_drone_template()
        upgrade_drone_color_animations_and_drone_materials()
        set_solid_shading_color_type_to_object()

        return {"FINISHED"}
