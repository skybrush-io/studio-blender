from bpy.types import Material, Operator
from typing import Optional

from sbstudio.plugin.constants import Collections, Templates
from sbstudio.plugin.materials import get_material_for_led_light_color

__all__ = ("DetachMaterialsFromDroneTemplateOperator",)


def detach_material_from_drone_template(
    drone, template_material: Optional[Material] = None
) -> None:
    if template_material is None:
        template = Templates.find_drone(create=False)
        template_material = (
            get_material_for_led_light_color(template) if template else None
        )

    if template_material is None:
        return

    for slot in drone.material_slots:
        if slot.material == template_material:
            copied_material = template_material.copy()
            copied_material.name = f"LED color of {drone.name}"
            slot.material = copied_material


class DetachMaterialsFromDroneTemplateOperator(Operator):
    """Detaches the materials of the drones from the template that the drones
    were created from.
    """

    bl_idname = "skybrush.detach_materials_from_drone_template"
    bl_label = "Detach Materials from Drone Template"

    def execute(self, context):
        template = Templates.find_drone(create=False)
        template_material = (
            get_material_for_led_light_color(template) if template else None
        )

        drones = Collections.find_drones()
        for drone in drones.objects:
            detach_material_from_drone_template(
                drone, template_material=template_material
            )

        return {"FINISHED"}
