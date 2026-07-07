from bpy.types import Collection, Context

from sbstudio.plugin.model.drone_groups import DroneGroupsProperties
from sbstudio.plugin.operators.base import DroneGroupOperator

__all__ = ("AddSelectedDronesToDroneGroupOperator",)


class AddSelectedDronesToDroneGroupOperator(DroneGroupOperator):
    """Adds the currently selected drones to the given drone group."""

    bl_idname = "skybrush.add_drones_selected_to_drone_group"
    bl_label = "Add Selected Drones"
    bl_description = "Adds the currently selected drones to the given drone group"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: Context):
        return DroneGroupOperator.poll(context) and context.selected_objects

    def execute_on_drone_group(
        self, group: Collection, drone_groups: DroneGroupsProperties, context: Context
    ):
        count = drone_groups.extend_group(group, context.selected_objects)
        if count > 1:
            self.report({"INFO"}, f"Added {count} drones to group '{group.name}'")
        elif count == 1:
            self.report({"INFO"}, f"Added drone to group '{group.name}'")

        return {"FINISHED"}
