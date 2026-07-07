from bpy.types import Collection, Context

from sbstudio.plugin.model.drone_groups import DroneGroupsProperties
from sbstudio.plugin.operators.base import DroneGroupOperator
from sbstudio.plugin.selection import select_only

__all__ = ("SelectDronesFromDroneGroup",)


class SelectDronesFromDroneGroup(DroneGroupOperator):
    """Selects the drones from the currently selected drone group."""

    bl_idname = "skybrush.select_drones_from_drone_group"
    bl_label = "Select Drones from Drone Group"
    bl_description = "Select the drones from the currently selected drone group"
    bl_options = {"REGISTER", "UNDO"}

    def execute_on_drone_group(
        self, group: Collection, drone_groups: DroneGroupsProperties, context: Context
    ):
        select_only(group.objects, context=context)
        return {"FINISHED"}
