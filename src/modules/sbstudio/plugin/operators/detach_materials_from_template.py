from bpy.types import Operator

from sbstudio.plugin.constants import Collections, Templates
from sbstudio.plugin.materials import (
    detach_pyro_material_from_drone_template,
    get_material_for_pyro,
)

__all__ = ("DetachMaterialsFromDroneTemplateOperator",)


class DetachMaterialsFromDroneTemplateOperator(Operator):
    """Detaches the materials of the drones from the template that the drones
    were created from.
    """

    bl_idname = "skybrush.detach_materials_from_drone_template"
    bl_label = "Detach Materials from Drone Template"

    def execute(self, context):
        template = Templates.find_drone(create=False)
        pyro_template_material = get_material_for_pyro(template) if template else None

        drones = Collections.find_drones()
        for drone in drones.objects:
            detach_pyro_material_from_drone_template(
                drone, template_material=pyro_template_material
            )

        return {"FINISHED"}
