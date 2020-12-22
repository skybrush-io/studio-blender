from bpy.types import Operator

__all__ = ("ValidateTrajectoriesOperator",)


class ValidateTrajectoriesOperator(Operator):
    """Validates the trajectories of the drones in a given frame range."""

    bl_idname = "skybrush.validate_trajectories"
    bl_label = "Validate Trajectories"
    bl_description = "Validates the trajectories of the drones in a given frame range."

    def execute(self, context):
        # TODO(ntamas)
        return {"FINISHED"}
