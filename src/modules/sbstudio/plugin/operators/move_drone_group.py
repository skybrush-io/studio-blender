from bpy.types import Collection, Context

from sbstudio.plugin.model.drone_groups import DroneGroupsProperties

from .base import DroneGroupOperator

__all__ = ("MoveDroneGroupDownOperator", "MoveDroneGroupUpOperator")


class MoveDroneGroupDownOperator(DroneGroupOperator):
    """Blender operator that moves the selected drone group one slot down
    in the drone groups list.
    """

    bl_idname = "skybrush.move_drone_group_down"
    bl_label = "Move Selected Drone Group Down"
    bl_description = (
        "Moves the selected drone group down by one slot in the drone groups list"
    )

    @classmethod
    def poll(cls, context):
        if not DroneGroupOperator.poll(context):
            return False

        drone_groups = context.scene.skybrush.drone_groups
        if drone_groups.active_group is None:
            return False

        from sbstudio.plugin.constants import Collections

        group_collection = Collections.find_drone_groups(create=False)
        if not group_collection:
            return False

        return (
            drone_groups.active_group is not None
            and drone_groups.active_group_index < len(group_collection.children) - 1
        )

    def execute_on_drone_group(
        self, group: Collection, drone_groups: DroneGroupsProperties, context: Context
    ) -> set[str]:
        drone_groups.move_active_group_down()
        return {"FINISHED"}


class MoveDroneGroupUpOperator(DroneGroupOperator):
    """Blender operator that moves the selected drone group one slot up
    in the drone groups list.
    """

    bl_idname = "skybrush.move_drone_group_up"
    bl_label = "Move Selected Drone Group Up"
    bl_description = (
        "Moves the selected drone group up by one slot in the drone groups list"
    )

    @classmethod
    def poll(cls, context):
        if not DroneGroupOperator.poll(context):
            return False

        drone_groups = context.scene.skybrush.drone_groups
        if drone_groups.active_group is None:
            return False

        return (
            drone_groups.active_group is not None
            and drone_groups.active_group_index > 0
        )

    def execute_on_drone_group(
        self, group: Collection, drone_groups: DroneGroupsProperties, context: Context
    ) -> set[str]:
        drone_groups.move_active_group_up()
        return {"FINISHED"}
