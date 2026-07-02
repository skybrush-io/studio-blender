from bpy.types import Collection, Context

from sbstudio.plugin.model.drone_groups import DroneGroupsProperties

from .base import DroneGroupOperator

__all__ = ("RemoveDroneGroupOperator",)


class RemoveDroneGroupOperator(DroneGroupOperator):
    """Removes the currently selected drone group from the list of drone groups."""

    bl_idname = "skybrush.remove_drone_group"
    bl_label = "Remove Drone Group"
    bl_description = "Removes the currently selected drone group"
    bl_options = {"REGISTER", "UNDO"}

    def execute_on_drone_group(
        self, group: Collection, drone_groups: DroneGroupsProperties, context: Context
    ) -> set[str]:
        drone_groups.remove_group(group)
        return {"FINISHED"}
