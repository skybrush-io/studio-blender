import bpy
import logging

from time import time

from sbstudio.plugin.actions import ensure_action_exists_for_object
from sbstudio.plugin.constants import Collections, Templates
from sbstudio.plugin.errors import SkybrushStudioAddonError
from sbstudio.plugin.keyframes import get_keyframes, set_keyframes
from sbstudio.plugin.materials import (
    get_material_for_led_light_color,
    _get_shader_node_and_input_for_diffuse_color_of_material,
)
from sbstudio.plugin.operators.base import MigrationOperator

__all__ = ("UseSharedMaterialForAllDronesMigrationOperator",)

log = logging.getLogger(__name__)


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


def set_all_shading_color_types_to_object() -> None:
    """Sets the object color source of the solid and wireframe
    shading types of the 3D Viewport to use object color."""
    shading = getattr(bpy.context.space_data, "shading", None)
    if shading is None:
        log.warning(
            "Space data does not have a 'shading' property. "
            "Set Object Color and Wireframe color to Object "
            "in your 3D Viewport's Viewport Shading properties manually!"
        )
        return

    shading.color_type = "OBJECT"
    shading.wireframe_color_type = "OBJECT"


def upgrade_drone_color_animations_and_drone_materials() -> None:
    """Moves drone color animation from shader nodes to object colors
    and replaces drone material with template material."""
    template = Templates.find_drone(create=False)
    template_material = get_material_for_led_light_color(template)
    drones = Collections.find_drones()
    num_drones = len(drones.objects)
    last_log = time()
    for i, drone in enumerate(drones.objects):
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
        if time() - last_log > 10 or i == num_drones - 1:
            log.info(
                f"{(i + 1) / num_drones * 100:.1f}% ready, "
                f"{i + 1}/{num_drones} drones converted"
            )
            last_log = time()


def needs_migration():
    """Returns whether the current Blender content needs migration."""
    # TODO: what should be the optimal method to check if file
    # needs migration or not? We check the template material now
    # as it is most probably not modified by the users frequently
    try:
        template = Templates.find_drone(create=False)
    except (KeyError, ValueError):
        return False

    template_material = get_material_for_led_light_color(template)
    if template_material is None:
        return False

    _, input = _get_shader_node_and_input_for_diffuse_color_of_material(
        template_material
    )

    return not input.is_linked


class UseSharedMaterialForAllDronesMigrationOperator(MigrationOperator):
    """Upgrades old Skybrush Studio for Blender file content (<=3.13.2)
    that uses a separate material for all drone objects to a new version
    in which all drones share a common material. This speeds up light effect
    handling substantially.
    """

    bl_idname = "skybrush.use_shared_material_for_all_drones_migration"
    bl_label = "Update file content to speed up light effect rendering"
    bl_description = (
        "Upgrade your old (<=3.13.2) Skybrush Studio for Blender file content\n"
        "to speed up light effect playback and show export, by replacing all\n"
        "drone object materials to a shared template material, modifying its shader\n"
        "node tree and storing color animations in the drone object's 'color' property\n"
    )

    def execute_migration(self, context):
        """Executes the migration/upgrade on the current Blender content."""

        log.info("Upgrade started.")

        log.info("Modifying shader node tree of drone template...")
        add_object_info_to_shader_node_tree_of_drone_template()

        log.info("Simplifying drone color animation storage...")
        upgrade_drone_color_animations_and_drone_materials()

        log.info("Changing 3D Viewport shader color types to 'OBJECT'...")
        set_all_shading_color_types_to_object()

        log.info("Upgrade successful.")

        return {"FINISHED"}

    def needs_migration(self) -> bool:
        """Returns whether the current Blender content needs migration."""
        return needs_migration()
