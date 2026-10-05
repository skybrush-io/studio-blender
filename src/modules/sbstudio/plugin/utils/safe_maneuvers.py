"""Install checked offline maneuvers without changing existing show animation."""

import json
from dataclasses import dataclass
from math import isfinite

import bpy
import numpy as np
from bpy.types import Action, CopyLocationConstraint, Object
from mathutils import Vector

from sbstudio.math.safe_maneuvers import ManeuverLimits, SynchronizedManeuver
from sbstudio.plugin.actions import (
    _iter_all_f_curves_and_bags,
    ensure_f_curve_exists_for_data_path_and_index,
)
from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.local_api import LocalSkybrushStudioAPI
from sbstudio.plugin.model.formation import create_marker, remove_formation
from sbstudio.plugin.model.storyboard import StoryboardEntryPurpose
from sbstudio.plugin.utils.evaluator import create_position_evaluator
from sbstudio.plugin.utils.transition import create_transition_constraint_between
from sbstudio.timing import effective_fps


@dataclass
class _Attachment:
    drone: Object
    constraint: CopyLocationConstraint
    data_path: str
    had_animation: bool
    original_action: Action | None
    new_action: Action | None = None


def _check_animation_support(drones, context):
    if abs(context.scene.unit_settings.scale_length - 1) > 1e-6:
        raise ValueError("Checked maneuvers require metre-scale scene units (scale 1)")
    for drone in drones:
        if drone.library or drone.rigid_body:
            raise ValueError(
                f"{drone.name}: linked/rigid-body drones are not supported"
            )
        animation = drone.animation_data
        if not animation:
            continue
        if (
            animation.drivers
            or (
                animation.use_nla
                and any(
                    not track.mute and track.strips for track in animation.nla_tracks
                )
            )
            or animation.action_blend_type != "REPLACE"
            or animation.action_influence != 1
        ):
            raise ValueError(
                f"{drone.name}: drivers or blended/NLA actions need separate review"
            )
        action = animation.action
        if action and (action.library or action.users > 1 or len(action.layers) > 1):
            raise ValueError(
                f"{drone.name}: use a local, single-user, single-layer action"
            )


def _write_marker_curves(marker, plan, index):
    marker.animation_data_create()
    marker.animation_data.action = bpy.data.actions.new(f"{marker.name} Action")
    for axis in range(3):
        curve = ensure_f_curve_exists_for_data_path_and_index(
            marker, data_path="location", index=axis
        )
        for frame, point in zip(plan.frames, plan.positions[:, index, :]):
            key = curve.keyframe_points.insert(
                frame, float(point[axis]), options={"FAST"}
            )
            key.interpolation = "BEZIER"
            key.handle_left_type = key.handle_right_type = "FREE"
        # Insertions can invalidate Blender keyframe references. Re-fetch them.
        curve.update()
        for phase, (right, left) in enumerate(plan.handles):
            a, b = curve.keyframe_points[phase], curve.keyframe_points[phase + 1]
            a.handle_right = Vector((right, a.co.y))
            b.handle_left = Vector((left, b.co.y))
        curve.extrapolation = "CONSTANT"
        curve.update()
        for phase, (right, left) in enumerate(plan.handles):
            a, b = curve.keyframe_points[phase], curve.keyframe_points[phase + 1]
            if tuple(a.handle_right) != (
                right,
                float(plan.positions[phase, index, axis]),
            ) or tuple(b.handle_left) != (
                left,
                float(plan.positions[phase + 1, index, axis]),
            ):
                raise ValueError(
                    "Blender changed the checked Bezier handles; maneuver not installed"
                )


def install_maneuver(plan: SynchronizedManeuver, drones, storyboard, *, name, context):
    """Attach independent world-space markers with a step influence at handoff.

    No existing keys/constraints are removed or retimed. The new constraint is
    last, world-space, full influence from the handoff onward. The source pose
    is held for one frame, avoiding interpolation against a moving prior target.
    Locked manual-mapped entries prevent ordinary transition recalculation from
    replacing the route. Explicit later editing invalidates this construction.
    """
    _check_animation_support(drones, context)
    scene = context.scene
    original_frame = scene.frame_current, scene.frame_subframe
    original_active = storyboard.active_entry_index
    original_formations = Collections.find_formations(create=False)
    formations = None
    formation = None
    attached = []
    marker_actions = []
    try:
        formation = bpy.data.collections.new(name)
        formations = Collections.find_formations()
        formations.children.link(formation)
        markers = []
        for index, point in enumerate(plan.positions[0]):
            marker = create_marker(
                tuple(point), f"{formation.name} - {index + 1}", collection=formation
            )
            markers.append(marker)
            try:
                _write_marker_curves(marker, plan, index)
            finally:
                if marker.animation_data and marker.animation_data.action:
                    marker_actions.append(marker.animation_data.action)

        entry = storyboard.add_new_entry(
            formation=formation,
            frame_start=plan.frames[0],
            duration=plan.frames[-1] - plan.frames[0] + 1,
            select=True,
            purpose=StoryboardEntryPurpose.LANDING,
            context=context,
        )
        if entry is None:
            raise ValueError("Could not create the checked maneuver storyboard entry")
        entry.transition_type = "MANUAL"
        entry.transition_velocity_profile = "LINEAR"
        entry.update_mapping(list(range(len(drones))))
        entry.is_locked = True
        formation["skybrush_maneuver"] = json.dumps(plan.report(), allow_nan=False)

        for drone, marker in zip(drones, markers, strict=True):
            had_animation = drone.animation_data is not None
            original_action = drone.animation_data.action if had_animation else None
            constraint = create_transition_constraint_between(drone, entry)
            data_path = constraint.path_from_id("influence")
            state = _Attachment(
                drone, constraint, data_path, had_animation, original_action
            )
            attached.append(state)
            if original_action is None:
                drone.animation_data_create()
                drone.animation_data.action = bpy.data.actions.new(
                    f"{drone.name} Maneuver"
                )
                state.new_action = drone.animation_data.action
            constraint.target = marker
            constraint.owner_space = constraint.target_space = "WORLD"
            constraint.use_offset = False
            curve = ensure_f_curve_exists_for_data_path_and_index(
                drone, data_path=data_path, index=0
            )
            for frame, value in ((plan.frames[0] - 2, 0), (plan.frames[0] - 1, 1)):
                curve.keyframe_points.insert(frame, value).interpolation = "CONSTANT"
            curve.extrapolation = "CONSTANT"
            curve.update()

        # Construction checks plus an evaluated smoke check at every boundary.
        # The continuous proof is the shared cubic model, not these samples.
        for frame, positions in zip(plan.frames, plan.positions):
            scene.frame_set(frame)
            actual = np.asarray(
                [tuple(drone.matrix_world.translation) for drone in drones]
            )
            if not np.allclose(actual, positions, rtol=0, atol=1e-4):
                raise ValueError(
                    "Evaluated drones do not follow the checked world-space paths"
                )
        return True
    except Exception:
        # Roll back only data introduced by this installation, including curves
        # on existing actions. Do not clean unrelated stale user F-curves.
        for state in reversed(attached):
            drone = state.drone
            for curve, bag in list(_iter_all_f_curves_and_bags(drone.animation_data)):
                if curve.data_path == state.data_path:
                    bag.fcurves.remove(curve)
            drone.constraints.remove(state.constraint)
            if state.original_action is None and drone.animation_data:
                drone.animation_data.action = None
                if not state.had_animation:
                    drone.animation_data_clear()
            if state.new_action is not None and state.new_action.users == 0:
                bpy.data.actions.remove(state.new_action)
        if formation is not None:
            for index in range(len(storyboard.entries) - 1, -1, -1):
                if storyboard.entries[index].formation == formation:
                    storyboard.entries.remove(index)
            remove_formation(formation)
        if (
            original_formations is None
            and formations is not None
            and not formations.children
            and not formations.objects
        ):
            bpy.data.collections.remove(formations)
        for action in marker_actions:
            if action.users == 0:
                bpy.data.actions.remove(action)
        storyboard.active_entry_index = original_active
        storyboard._regenerate_entries_or_transitions()
        raise
    finally:
        scene.frame_set(original_frame[0], subframe=original_frame[1])


def run_offline_maneuver(operator, storyboard, *, context, return_home=False):
    """Offline UI entry point: all feasibility checks precede scene mutation."""
    try:
        if storyboard.last_entry is None:
            raise ValueError("Create a storyboard before planning a checked maneuver")
        if operator.start_frame != storyboard.frame_end:
            raise ValueError(
                f"Start a checked maneuver at the last storyboard frame ({storyboard.frame_end}). "
                "Extend and check the preceding show separately if a later start is needed."
            )
        drones = list(Collections.find_drones().objects)
        _check_animation_support(drones, context)
        safety = context.scene.skybrush.safety_check
        settings = context.scene.skybrush.settings
        vertical = operator.velocity_z if return_home else operator.velocity
        requested = [
            operator.spacing,
            operator.velocity,
            vertical,
            settings.max_acceleration,
            safety.proximity_warning_threshold,
            safety.altitude_warning_threshold,
            safety.velocity_xy_warning_threshold,
            safety.effective_velocity_z_threshold_up,
            safety.effective_velocity_z_threshold_down,
            safety.acceleration_warning_threshold,
        ]
        if any(not isfinite(v) or v <= 0 for v in requested):
            raise ValueError(
                "Requested spacing, speeds and acceleration must be finite and positive"
            )
        limits = ManeuverLimits(
            min_distance=max(operator.spacing, safety.proximity_warning_threshold),
            max_altitude=safety.altitude_warning_threshold,
            max_velocity_xy=min(operator.velocity, safety.velocity_xy_warning_threshold)
            if return_home
            else safety.velocity_xy_warning_threshold,
            max_velocity_z=min(
                vertical,
                safety.effective_velocity_z_threshold_up,
                safety.effective_velocity_z_threshold_down,
            ),
            max_acceleration=min(
                settings.max_acceleration, safety.acceleration_warning_threshold
            ),
        )
        original_frame = context.scene.frame_current, context.scene.frame_subframe
        try:
            with create_position_evaluator(context=context) as evaluate:
                source = evaluate(drones, frame=operator.start_frame)
                home = (
                    evaluate(drones, frame=storyboard.frame_start)
                    if return_home
                    else None
                )
        finally:
            context.scene.frame_set(original_frame[0], subframe=original_frame[1])
        parameters = {
            "limits": limits,
            "fps": effective_fps(context.scene.render),
            "start_frame": operator.start_frame + 1,
        }
        with call_api_from_blender_operator(
            operator, "checked offline maneuver planner"
        ) as api:
            if not isinstance(api, LocalSkybrushStudioAPI):
                raise RuntimeError(
                    "Checked local maneuvers require Offline design mode"
                )
            if return_home:
                assert home is not None
                target = (
                    [(x, y, operator.altitude) for x, y, _ in home]
                    if operator.to_aerial_grid
                    else home
                )
                plan = api.plan_smart_rth(
                    source,
                    target,
                    cruise_altitude=operator.altitude,
                    landing_velocity=None
                    if operator.to_aerial_grid
                    else min(vertical, 0.5),
                    layer_height=operator.altitude_shift
                    if operator.to_aerial_grid
                    else 0,
                    **parameters,
                )
            else:
                plan = api.plan_checked_landing(
                    source, target_altitude=operator.altitude, **parameters
                )
        install_maneuver(
            plan,
            drones,
            storyboard,
            name="Checked return to home" if return_home else "Checked landing",
            context=context,
        )
        operator.report(
            {"INFO"},
            "Checked maneuver created and locked. Re-export and review the complete show; this is not flight approval.",
        )
        return True
    except (ValueError, RuntimeError) as exc:
        operator.report({"ERROR"}, str(exc))
        return False
