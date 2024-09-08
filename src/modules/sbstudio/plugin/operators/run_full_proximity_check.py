from numpy import array, float32
from typing import Literal

from bpy.types import Context, Operator

from sbstudio.math.nearest_neighbors import find_all_point_pairs_closer_than
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.tasks.safety_check import (
    create_position_snapshot_for_drones_in_collection,
)


__all__: tuple[Literal["RunFullProximityCheckOperator"]] = (
    "RunFullProximityCheckOperator",
)


class RunFullProximityCheckOperator(Operator):
    """Executes an all-pairs proximity check on the drones in the current frame."""

    bl_idname = "skybrush.run_full_proximity_check"
    bl_label = "Calculate All Proximity Warnings"
    bl_description = (
        "Runs an all-pairs proximity check on all the drones. This check does "
        "not stop after the first pair of drones that are closer to each other "
        "than the proximity threshold"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: Context):
        drones = Collections.find_drones(create=False)
        return drones is not None

    def execute(self, context: Context):
        safety_check = context.scene.skybrush.safety_check
        drones = Collections.find_drones(create=False)
        if not drones:
            return

        frame = context.scene.frame_current
        snapshot = create_position_snapshot_for_drones_in_collection(
            drones, frame=frame
        )
        positions = array(list(snapshot.values()), dtype=float32)

        threshold = max(safety_check.proximity_warning_threshold, 0)

        safety_check.set_safety_check_result(
            all_close_pairs=find_all_point_pairs_closer_than(positions, threshold)
        )

        self.report({"INFO"}, "Calculation completed")
        return {"FINISHED"}
