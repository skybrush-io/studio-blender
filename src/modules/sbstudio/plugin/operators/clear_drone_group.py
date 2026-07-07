import bpy
from bpy.types import Collection, Context

from sbstudio.plugin.model.drone_groups import DroneGroupsProperties, get_drone_groups
from sbstudio.plugin.operators.base import DroneGroupOperator
from sbstudio.plugin.utils.collections import unlink_all_objects_from_collection

__all__ = ("ClearDroneGroupOperator",)


class ClearDroneGroupOperator(DroneGroupOperator):
    """Removes all drones from the given drone group."""

    bl_idname = "skybrush.clear_drone_group"
    bl_label = "Clear Drone Group"
    bl_description = "Removes all drones from the given drone group"
    bl_options = {"REGISTER", "UNDO"}

    drone_group: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context: Context):
        if not DroneGroupOperator.poll(context):
            return False

        group = get_drone_groups(context=context).active_group
        if group is not None and group.objects:
            return True

        return False

    def execute_on_drone_group(
        self, group: Collection, drone_groups: DroneGroupsProperties, context: Context
    ):
        count = unlink_all_objects_from_collection(group, recursive=True)
        if count > 1:
            self.report({"INFO"}, f"Removed {count} objects from group '{group.name}'")
        elif count == 1:
            self.report({"INFO"}, f"Removed 1 object from group '{group.name}'")
        return {"FINISHED"}
