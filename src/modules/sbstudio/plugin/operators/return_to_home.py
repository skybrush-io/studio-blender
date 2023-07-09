import bpy

from bpy.props import FloatProperty, IntProperty
from bpy.types import Context, Object
from math import ceil, sqrt

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.model.formation import create_formation

from .base import StoryboardOperator
from .takeoff import create_helper_formation_for_takeoff_and_landing

__all__ = ("ReturnToHomeOperator",)


class ReturnToHomeOperator(StoryboardOperator):
    """Blender operator that adds a return-to-home transition to the show."""

    bl_idname = "skybrush.rth"
    bl_label = "Return Drones to Home Positions"
    bl_description = "Add a return-to-home maneuver to all the drones"
    bl_options = {"REGISTER", "UNDO"}

    only_with_valid_storyboard = True

    start_frame = IntProperty(
        name="at frame", description="Start frame of the return-to-home maneuver"
    )

    velocity = FloatProperty(
        name="with velocity",
        description="Average velocity during the return-to-home maneuver",
        default=4,
        min=0.1,
        soft_min=0.1,
        soft_max=10,
        unit="VELOCITY",
    )

    altitude = FloatProperty(
        name="to altitude",
        description="Altitude to return-to-home to",
        default=10,
        soft_min=-50,
        soft_max=50,
        unit="LENGTH",
    )

    altitude_shift = FloatProperty(
        name="Layer height",
        description=(
            "Specifies the difference between altitudes of landing layers "
            "for multi-phase landings when multiple drones occupy the same "
            "slot within safety distance."
        ),
        default=5,
        soft_min=0,
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

        first_frame = storyboard.frame_start
        source, target, _ = create_helper_formation_for_takeoff_and_landing(
            drones,
            frame=first_frame,
            base_altitude=self.altitude,
            layer_height=self.altitude_shift,
            min_distance=context.scene.skybrush.safety_check.proximity_warning_threshold,
        )

        diffs = [
            sqrt((s[0] - t[0]) ** 2 + (s[1] - t[1]) ** 2 + (s[2] - t[2]) ** 2)
            for s, t in zip(source, target)
        ]

        # Calculate RTH duration from max distance to travel and the
        # average velocity
        max_distance = max(diffs)
        fps = context.scene.render.fps
        rth_duration = ceil((max_distance / self.velocity) * fps)

        # Extend the duration of the last formation to the frame where we want
        # to start the RTH maneuver
        if len(storyboard.entries) > 0:
            storyboard.last_entry.extend_until(self.start_frame)

        # Calculate when the RTH should end
        end_of_rth = self.start_frame + rth_duration

        # Add a new storyboard entry with the given formation
        storyboard.add_new_entry(
            formation=create_formation("Return to home", target),
            frame_start=end_of_rth,
            duration=0,
            select=True,
            context=context,
        )

        # Recalculate the transition leading to the target formation
        bpy.ops.skybrush.recalculate_transitions(scope="TO_SELECTED")
        return True

    def _validate_start_frame(self, context: Context) -> bool:
        """Returns whether the return to home time chosen by the user is valid."""
        storyboard = context.scene.skybrush.storyboard
        if storyboard.last_entry is not None:
            last_frame = context.scene.skybrush.storyboard.frame_end
        else:
            last_frame = None

        # TODO(ntamas): what if the last entry in the storyboard _is_ the
        # RTH, what shall we do then? Probably we should ignore it and look
        # at the penultimate entry.

        if last_frame is not None and self.start_frame < last_frame:
            self.report(
                {"ERROR"},
                f"Return to home maneuver must not start before the last entry "
                f"of the storyboard (frame {last_frame})",
            )
            return False

        return True
