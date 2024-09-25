import bpy

from bpy.props import FloatProperty, IntProperty, BoolProperty
from bpy.types import Context
from functools import partial
from math import ceil, sqrt

from sbstudio.errors import SkybrushStudioError
from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.actions import (
    ensure_action_exists_for_object,
    find_f_curve_for_data_path_and_index,
)
from sbstudio.plugin.model.formation import create_formation, get_markers_from_formation
from sbstudio.plugin.model.safety_check import get_proximity_warning_threshold
from sbstudio.plugin.model.storyboard import get_storyboard
from sbstudio.plugin.utils.evaluator import create_position_evaluator

from .base import StoryboardOperator
from .takeoff import create_helper_formation_for_takeoff_and_landing

__all__ = ("ReturnToHomeOperator",)


def is_smart_rth_enabled_globally() -> bool:
    # Smart RTH used to be an experimental feature but we are now releasing it
    # for testing by a larger audience.
    return True


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
        description="Average horizontal velocity during the return-to-home maneuver",
        default=4,
        min=0.1,
        soft_min=0.1,
        soft_max=10,
        unit="VELOCITY",
    )

    velocity_z = FloatProperty(
        name="with velocity Z",
        description="Average vertical velocity during the return-to-home maneuver",
        default=2,
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
            "slot within safety distance"
        ),
        default=5,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    use_smart_rth = BoolProperty(
        name="Use smart RTH",
        description=(
            "Enable the smart return to home function that ensures that "
            "all drones return to their own home position with an optimal "
            "collision free smart transition"
        ),
        default=False,
    )

    @classmethod
    def poll(cls, context):
        if not super().poll(context):
            return False

        drones = Collections.find_drones(create=False)
        return drones is not None and len(drones.objects) > 0

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        use_smart_rth = self._should_use_smart_rth()

        layout.prop(self, "start_frame")
        if use_smart_rth:
            # TODO: labels XY and Z consume too much space...
            row = layout.row()
            row.prop(self, "velocity")
            row.separator()
            row.label(text="XY")
            row.separator()
            row.prop(self, "velocity_z", text="")
            row.separator()
            row.label(text="Z")
        else:
            layout.prop(self, "velocity")
        layout.prop(self, "altitude")
        if not use_smart_rth:
            layout.prop(self, "altitude_shift")

        if is_smart_rth_enabled_globally():
            layout.prop(self, "use_smart_rth")

    def invoke(self, context, event):
        self.start_frame = max(
            context.scene.frame_current, get_storyboard(context=context).frame_end
        )
        return context.window_manager.invoke_props_dialog(self)

    def execute_on_storyboard(self, storyboard, entries, context):
        try:
            success = self._run(storyboard, context=context)
        except SkybrushStudioError:
            # These are handled nicely
            success = False
        return {"FINISHED"} if success else {"CANCELLED"}

    def _should_use_smart_rth(self) -> bool:
        return self.use_smart_rth and is_smart_rth_enabled_globally()

    def _run(self, storyboard, *, context) -> bool:
        bpy.ops.skybrush.prepare()

        if not self._validate_start_frame(context):
            return False

        drones = Collections.find_drones().objects
        if not drones:
            return False

        use_smart_rth = self._should_use_smart_rth()
        self.start_frame = max(self.start_frame, storyboard.frame_end) + (
            1 if use_smart_rth else 0
        )

        with create_position_evaluator() as get_positions_of:
            source = get_positions_of(drones, frame=self.start_frame)

        first_frame = storyboard.frame_start
        _, target, _ = create_helper_formation_for_takeoff_and_landing(
            drones,
            frame=first_frame,
            base_altitude=self.altitude,
            layer_height=self.altitude_shift if not use_smart_rth else 0,
            min_distance=get_proximity_warning_threshold(context),
            operator=self,
        )
        fps = context.scene.render.fps

        if use_smart_rth:
            # Set up non-trivial parameters
            # TODO: get them as explicit parameter if needed
            settings = getattr(context.scene.skybrush, "settings", None)
            max_acceleration = settings.max_acceleration if settings else 4
            min_distance = get_proximity_warning_threshold(context)
            land_speed = min(self.velocity_z, 0.5)

            # call API to create smart RTH plan
            with call_api_from_blender_operator(self) as api:
                plan = api.plan_smart_rth(
                    source,
                    target,
                    max_velocity_xy=self.velocity,
                    max_velocity_z=self.velocity_z,
                    max_acceleration=max_acceleration,
                    min_distance=min_distance,
                    rth_model="straight_line_with_neck",
                )
            if not plan.start_times or not plan.durations:
                return False

            # Add a new storyboard entry for the smart RTH formation
            # TODO: What should happen if there is already a formation with the
            # same name?
            entry = storyboard.add_new_entry(
                formation=create_formation("Smart return to home", source),
                frame_start=self.start_frame,
                duration=int(ceil((plan.duration + self.altitude / land_speed) * fps)),
                select=True,
                context=context,
            )
            assert entry is not None
            markers = get_markers_from_formation(entry.formation)

            # generate smart RTH trajectories in the new formation
            for start_time, duration, inner_points, p, q, marker in zip(
                plan.start_times,
                plan.durations,
                plan.inner_points,
                source,
                target,
                markers,
                strict=True,
            ):
                action = ensure_action_exists_for_object(
                    marker, name=f"Animation data for {marker.name}", clean=True
                )

                f_curves = []
                for i in range(3):
                    f_curve = find_f_curve_for_data_path_and_index(
                        action, "location", i
                    )
                    if f_curve is None:
                        f_curve = action.fcurves.new("location", index=i)
                    else:
                        # We should clear the keyframes that fall within the
                        # range of our keyframes. Currently it's not needed because
                        # it's a freshly created marker so it can't have any
                        # keyframes that we don't know about.
                        print(f"Already existing F-curve! {marker.name} {i}")
                        pass
                    f_curves.append(f_curve)
                insert = [
                    partial(f_curve.keyframe_points.insert, options={"FAST"})
                    for f_curve in f_curves
                ]
                path_points = []
                if start_time > 0:
                    path_points.append((0, *p))
                path_points.append((start_time, *p))
                path_points.extend(tuple(inner_points))
                path_points.extend(
                    (
                        (start_time + duration, *q),
                        (
                            start_time + duration + self.altitude / land_speed,
                            q[0],
                            q[1],
                            0,  # TODO: starting position would be better than explicit 0
                        ),
                    )
                )
                for point in path_points:
                    frame = int(self.start_frame + point[0] * fps)
                    keyframes = (
                        insert[0](frame, point[1]),
                        insert[1](frame, point[2]),
                        insert[2](frame, point[3]),
                    )
                    for keyframe in keyframes:
                        keyframe.interpolation = "LINEAR"
                # Commit the insertions that we've made in "fast" mode
                for f_curve in f_curves:
                    f_curve.update()
        else:
            diffs = [
                sqrt((s[0] - t[0]) ** 2 + (s[1] - t[1]) ** 2 + (s[2] - t[2]) ** 2)
                for s, t in zip(source, target)
            ]

            # Calculate RTH duration from max distance to travel and the
            # average velocity
            max_distance = max(diffs)
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
        storyboard = get_storyboard(context=context)
        last_frame = storyboard.frame_end if storyboard.last_entry is not None else None

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
