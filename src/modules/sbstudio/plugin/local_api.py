"""In-process backend used by the experimental offline design mode."""

from __future__ import annotations

import csv
import re
from bisect import bisect_right
from collections.abc import Sequence
from io import BytesIO, StringIO
from math import ceil, isclose
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sbstudio.api.errors import SkybrushStudioAPIError
from sbstudio.api.types import Limits, Version
from sbstudio.atomic_file import atomic_write_bytes
from sbstudio.export_policy import (
    CHECKED,
    DEFAULT_MAX_EXPORT_DEVIATION,
    evaluate_export_gate,
    validate_export_policy,
)
from sbstudio.math.local_planner import (
    decompose_points_locally,
    match_points_locally,
    plan_landing_locally,
    plan_transition_locally,
)
from sbstudio.math.motion_audit import audit_sampled_motion
from sbstudio.math.safe_maneuvers import plan_checked_landing, plan_checked_rth
from sbstudio.math.trajectory_validation import validate_trajectories
from sbstudio.model.light_program import LightProgram
from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.model.time_markers import TimeMarkers
from sbstudio.model.trajectory import Trajectory
from sbstudio.model.types import Coordinate3D
from sbstudio.skyc import render_skyc_archive

__all__ = ("LocalSkybrushStudioAPI",)


_SAFE_FILENAME_PART = re.compile(r"[^A-Za-z0-9_.-]+")


def _unsupported(operation: str) -> SkybrushStudioAPIError:
    return SkybrushStudioAPIError(
        f"{operation} is not available in Offline design mode. "
        "Use the Community server, a licensed cloud service, or a licensed "
        "local Studio Server for this operation."
    )


def _sample_trajectory(
    trajectory: Trajectory, times: Sequence[float], time: float
) -> tuple[float, float, float]:
    points = trajectory.points
    if not points:
        raise SkybrushStudioAPIError("cannot export an empty trajectory")

    right = bisect_right(times, time)
    if right <= 0:
        point = points[0]
        return float(point.x), float(point.y), float(point.z)
    if right >= len(points):
        point = points[-1]
        return float(point.x), float(point.y), float(point.z)

    left_point, right_point = points[right - 1], points[right]
    duration = right_point.t - left_point.t
    ratio = (time - left_point.t) / duration if duration > 0 else 1.0
    return (
        float(left_point.x + ratio * (right_point.x - left_point.x)),
        float(left_point.y + ratio * (right_point.y - left_point.y)),
        float(left_point.z + ratio * (right_point.z - left_point.z)),
    )


def _sample_light(
    light_program: LightProgram | None,
    times: Sequence[float],
    time: float,
) -> tuple[int, int, int]:
    if light_program is None or not light_program.colors:
        return 255, 255, 255

    colors = light_program.colors
    right = bisect_right(times, time)
    if right <= 0:
        color = colors[0]
        return int(color.r), int(color.g), int(color.b)
    if right >= len(colors):
        color = colors[-1]
        return int(color.r), int(color.g), int(color.b)

    left_color, right_color = colors[right - 1], colors[right]
    if not right_color.is_fade:
        return int(left_color.r), int(left_color.g), int(left_color.b)

    duration = right_color.t - left_color.t
    ratio = (time - left_color.t) / duration if duration > 0 else 1.0
    result = tuple(
        int(round(left + ratio * (right_value - left)))
        for left, right_value in zip(
            (left_color.r, left_color.g, left_color.b),
            (right_color.r, right_color.g, right_color.b),
            strict=True,
        )
    )
    return result[0], result[1], result[2]


def _sample_times(trajectory: Trajectory, fps: float) -> list[float]:
    if fps <= 0:
        raise SkybrushStudioAPIError("CSV frame rate must be positive")
    if not trajectory.points:
        raise SkybrushStudioAPIError("cannot export an empty trajectory")

    start = float(trajectory.points[0].t)
    end = float(trajectory.points[-1].t)
    count = int(ceil(max(0.0, end - start) * fps))
    result = [start + index / fps for index in range(count + 1)]
    if result[-1] > end and not isclose(result[-1], end):
        result[-1] = end
    elif result[-1] < end and not isclose(result[-1], end):
        result.append(end)
    return result


def _safe_filenames(names: Sequence[str], *, suffix: str = ".csv") -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for index, name in enumerate(names, start=1):
        stem = _SAFE_FILENAME_PART.sub("_", name).strip("._") or f"Drone_{index}"
        candidate = stem
        duplicate_index = 2
        while candidate.casefold() in used:
            candidate = f"{stem}_{duplicate_index}"
            duplicate_index += 1
        used.add(candidate.casefold())
        result[name] = f"{candidate}{suffix}"
    return result


def _render_csv_zip(
    trajectories: dict[str, Trajectory],
    lights: dict[str, LightProgram] | None,
    *,
    fps: float,
) -> bytes:
    buffer = BytesIO()
    filenames = _safe_filenames(list(trajectories))
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, trajectory in trajectories.items():
            output = StringIO(newline="")
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(("Time_msec", "X", "Y", "Z", "R", "G", "B"))
            light_program = lights.get(name) if lights else None
            trajectory_times = [point.t for point in trajectory.points]
            light_times = (
                [color.t for color in light_program.colors] if light_program else []
            )
            for time in _sample_times(trajectory, fps):
                position = _sample_trajectory(trajectory, trajectory_times, time)
                color = _sample_light(light_program, light_times, time)
                writer.writerow(
                    (
                        round(time * 1000),
                        *(round(value, 3) for value in position),
                        *color,
                    )
                )
            archive.writestr(filenames[name], output.getvalue().encode("ascii"))
    return buffer.getvalue()


class LocalSkybrushStudioAPI:
    """Limited in-process implementation of the API needed for local design.

    SKYC output from this backend is an unoptimized draft archive. It does not
    replace server-grade validation or production flight preparation.
    """

    def get_limits(self) -> Limits:
        return Limits(features=["offline-design"])

    last_validation_report: dict | None = None

    def get_version(self) -> Version:
        # New enough to select plan_takeoff() instead of the legacy endpoint.
        return Version(2, 43, 0, build_metadata="offline")

    def match_points(
        self,
        source: Sequence[Coordinate3D],
        target: Sequence[Coordinate3D],
        *,
        radius: float | None = None,
    ):
        return match_points_locally(source, target, radius=radius or 0)

    def decompose_points(
        self,
        points: Sequence[Coordinate3D],
        *,
        min_distance: float,
        method: str = "greedy",
    ) -> list[int]:
        return decompose_points_locally(points, min_distance=min_distance)

    def plan_takeoff(
        self,
        points: Sequence[Coordinate3D],
        *,
        min_distance: float,
    ) -> list[int]:
        return decompose_points_locally(points, min_distance=min_distance)

    def plan_landing(
        self,
        points: Sequence[Coordinate3D],
        *,
        min_distance: float,
        velocity: float,
        target_altitude: float = 0,
        spindown_time: float = 5,
    ) -> tuple[list[float], list[float]]:
        try:
            return plan_landing_locally(
                points,
                min_distance=min_distance,
                velocity=velocity,
                target_altitude=target_altitude,
                spindown_time=spindown_time,
            )
        except ValueError as exc:
            raise SkybrushStudioAPIError(str(exc)) from exc

    def plan_transition(
        self,
        source: Sequence[Coordinate3D],
        target: Sequence[Coordinate3D],
        *,
        max_velocity_xy: float,
        max_velocity_z: float,
        max_acceleration: float,
        max_velocity_z_up: float | None = None,
        matching_method: str = "optimal",
    ):
        return plan_transition_locally(
            source,
            target,
            max_velocity_xy=max_velocity_xy,
            max_velocity_z=max_velocity_z,
            max_acceleration=max_acceleration,
            max_velocity_z_up=max_velocity_z_up,
        )

    def plan_checked_landing(self, *args, **kwargs):
        """Offline synchronized cubic plan, not a remote API polyline response."""
        try:
            return plan_checked_landing(*args, **kwargs)
        except ValueError as exc:
            raise SkybrushStudioAPIError(str(exc)) from exc

    def plan_smart_rth(self, *args, **kwargs):
        """Offline synchronized cubic plan, consumed by the offline UI path."""
        try:
            return plan_checked_rth(*args, **kwargs)
        except ValueError as exc:
            raise SkybrushStudioAPIError(str(exc)) from exc

    def create_formation_from_svg(self, *args, **kwargs):
        raise _unsupported("SVG formation sampling")

    def convert_show_to_csv(self, *args, **kwargs):
        raise _unsupported("DSS show conversion")

    def export(
        self,
        *,
        trajectories: dict[str, Trajectory],
        lights: dict[str, LightProgram] | None = None,
        output: str | Path | None = None,
        renderer: str | list[str] = "skyc",
        renderer_params: dict[str, Any] | list[dict[str, Any] | None] | None = None,
        validation: SafetyCheckParams | None = None,
        show_title: str | None = None,
        show_type: str = "outdoor",
        show_location: Any | None = None,
        show_segments: dict[str, tuple[float, float]] | None = None,
        time_markers: TimeMarkers | None = None,
        pyro_programs: dict[str, Any] | None = None,
        yaw_setpoints: dict[str, Any] | None = None,
        audio: Any | None = None,
        cameras: list[Any] | None = None,
        evaluated_motion: dict | None = None,
        evaluated_motion_sample_interval: float | None = None,
        export_policy: str = CHECKED,
        max_export_deviation: float = DEFAULT_MAX_EXPORT_DEVIATION,
        validation_progress=None,
        **kwargs,
    ) -> bytes | None:
        self.last_validation_report = None
        report = None
        if renderer not in ("csv", "skyc"):
            raise _unsupported("This export format")
        if renderer == "csv":
            if renderer_params is not None and not isinstance(renderer_params, dict):
                raise SkybrushStudioAPIError("invalid CSV renderer parameters")
            fps = float((renderer_params or {}).get("fps", 4))
            data = _render_csv_zip(trajectories, lights, fps=fps)
        else:
            validate_export_policy(export_policy, max_export_deviation)
            if export_policy == CHECKED and evaluated_motion is None:
                raise SkybrushStudioAPIError(
                    "Checked export requires a dense motion audit. Destination unchanged. "
                    "Preview-only export is available for inspecting unfinished designs."
                )
            if export_policy == CHECKED and yaw_setpoints:
                raise SkybrushStudioAPIError(
                    "Checked offline export does not yet validate yaw control"
                )
            if pyro_programs:
                raise _unsupported("Pyro-enabled SKYC export")
            if audio is not None:
                raise _unsupported("Audio-enabled SKYC export")
            if cameras:
                raise _unsupported("Camera-enabled SKYC export")
            if not trajectories:
                raise SkybrushStudioAPIError("cannot export an empty show")
            empty_trajectory = next(
                (
                    name
                    for name, trajectory in trajectories.items()
                    if not trajectory.points
                ),
                None,
            )
            if empty_trajectory is not None:
                raise SkybrushStudioAPIError(
                    f"cannot export an empty trajectory for {empty_trajectory!r}"
                )
            limits = validation or SafetyCheckParams()
            exported_paths = {
                name: [
                    [time, *position]
                    for time, position, _ in trajectory.as_dict(version=1)["points"]
                ]
                for name, trajectory in trajectories.items()
            }
            report = validate_trajectories(
                exported_paths,
                min_distance=limits.min_distance,
                max_altitude=limits.max_altitude,
                max_velocity_xy=limits.max_velocity_xy,
                max_velocity_z=limits.max_velocity_z,
                max_velocity_z_up=limits.max_velocity_z_up,
                max_acceleration=limits.max_acceleration,
                show_segments=show_segments,
                on_progress=(
                    lambda done, total: validation_progress(
                        "Exported path validation", done, total
                    )
                )
                if validation_progress
                else None,
            )
            if evaluated_motion is not None:
                audit = audit_sampled_motion(
                    evaluated_motion,
                    exported_paths,
                    expected_sample_interval=evaluated_motion_sample_interval,
                    min_distance=limits.min_distance,
                    max_altitude=limits.max_altitude,
                    max_velocity_xy=limits.max_velocity_xy,
                    max_velocity_z=limits.max_velocity_z,
                    max_velocity_z_up=limits.max_velocity_z_up,
                    max_acceleration=limits.max_acceleration,
                    show_segments=show_segments,
                    on_progress=(
                        lambda done, total: validation_progress(
                            "Dense motion validation", done, total
                        )
                    )
                    if validation_progress
                    else None,
                )
                report["evaluated_motion_audit"] = audit
                report["diagnostic_warnings"].extend(
                    "evaluated_motion_" + check
                    for check in audit["validation"]["failed_checks"]
                    + audit["validation"]["diagnostic_warnings"]
                )
            report["export_gate"] = evaluate_export_gate(
                report,
                exported_paths,
                policy=export_policy,
                max_export_deviation=max_export_deviation,
            )
            if report["export_gate"]["status"] == "blocked":
                raise SkybrushStudioAPIError(
                    "Checked export blocked; destination unchanged: "
                    + ", ".join(report["export_gate"]["blocking_reasons"])
                    + ". Fix the design/settings, or explicitly choose Preview only to inspect the report."
                )
            data = render_skyc_archive(
                trajectories,
                lights,
                validation=validation or SafetyCheckParams(),
                show_title=show_title,
                show_type=show_type,
                show_location=show_location,
                show_segments=show_segments,
                time_markers=time_markers or TimeMarkers(),
                yaw_setpoints=yaw_setpoints,
                validation_report=report,
            )
        if validation_progress:
            validation_progress("Ready to save export", 1, 1)
        if output is None:
            self.last_validation_report = report
            return data

        atomic_write_bytes(output, data)
        self.last_validation_report = report
        return None
