import bpy

from bpy.props import FloatProperty, IntProperty
from bpy.types import Context, Object
from math import ceil
from typing import List

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.formation import create_formation
from sbstudio.plugin.utils.evaluator import create_position_evaluator

from .base import StoryboardOperator

__all__ = ("LandOperator",)


class LandOperator(StoryboardOperator):
    """Blender operator that adds a landing transition to the show, starting at
    the current frame.
    """

    bl_idname = "skybrush.land"
    bl_label = "Land Drones"
    bl_description = "Add a landing maneuver to all the drones"
    bl_options = {"REGISTER", "UNDO"}

    only_with_valid_storyboard = True

    start_frame = IntProperty(
        name="at frame", description="Start frame of the landing maneuver"
    )

    velocity = FloatProperty(
        name="with velocity",
        description="Average vertical velocity during the landing maneuver",
        default=1,
        min=0.1,
        soft_min=0.1,
        soft_max=10,
        unit="VELOCITY",
    )

    altitude = FloatProperty(
        name="to altitude",
        description="Altitude to land to",
        default=0,
        soft_min=-50,
        soft_max=50,
        unit="LENGTH",
    )

    @classmethod
    def poll(cls, context):
        if not super().poll(context):
            return False

        drones = Collections.find_drones(create=False)
        return drones is not None and len(drones.objects) > 0

    def invoke(self, context, event):
        storyboard = context.scene.skybrush.storyboard
        self.start_frame = max(context.scene.frame_current, storyboard.frame_end)
        return context.window_manager.invoke_props_dialog(self)

    def execute_on_storyboard(self, storyboard, entries, context):
        return {"FINISHED"} if self._run(storyboard, context=context) else {"CANCELLED"}

    def _run(self, storyboard, *, context) -> bool:
        bpy.ops.skybrush.prepare()

        if not self._validate_start_frame(context):
            return False

        drones = Collections.find_drones().objects
        if not drones:
            return False

        self._sort_drones(drones)

        # Prepare the points of the target formation to land to
        with create_position_evaluator() as get_positions_of:
            source = get_positions_of(drones, frame=self.start_frame)

        target = [(x, y, self.altitude) for x, y, z in source]

        diffs = [s[2] - t[2] for s, t in zip(source, target)]
        if min(diffs) < 0:
            dist = abs(min(diffs))
            self.report(
                {"ERROR"},
                f"At least one drone would have to land upwards by {dist}m",
            )
            return False

        # Calculate landing duration from max distance to travel and the
        # average velocity
        max_distance = max(diffs)
        fps = context.scene.render.fps
        landing_duration = ceil((max_distance / self.velocity) * fps)

        # Extend the duration of the last formation to the frame where we want
        # to start the landing
        if len(storyboard.entries) > 0:
            last_entry = storyboard.entries[-1]
            last_entry.extend_until(self.start_frame)

        # Calculate when the landing should end
        end_of_landing = self.start_frame + landing_duration

        # Add a new storyboard entry with the given formation
        storyboard.add_new_entry(
            formation=create_formation("Landing", target),
            frame_start=end_of_landing,
            duration=0,
            select=True,
            context=context,
        )

        # Recalculate the transition leading to the target formation
        bpy.ops.skybrush.recalculate_transitions(scope="TO_SELECTED")
        return True

    def _sort_drones(self, drones: List[Object]):
        """Sorts the given list of drones in-place according to the order
        specified by the user in this operator.
        """
        # TODO(ntamas): add support for ordering the drones
        pass

    def _validate_start_frame(self, context: Context) -> bool:
        """Returns whether the takeoff time chosen by the user is valid."""
        storyboard = context.scene.skybrush.storyboard
        if storyboard.last_entry is not None:
            last_frame = context.scene.skybrush.storyboard.frame_end
        else:
            last_frame = None

        # TODO(ntamas): what if the last entry in the storyboard _is_ the
        # landing, what shall we do then? Probably we should ignore it and look
        # at the penultimate entry.

        if last_frame is not None and self.start_frame < last_frame:
            self.report(
                {"ERROR"},
                f"Landing maneuver must not start before the last entry of the storyboard (frame {last_frame})",
            )
            return False

        return True
