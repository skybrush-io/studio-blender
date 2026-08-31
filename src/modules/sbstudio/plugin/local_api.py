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
from sbstudio.math.local_planner import (
    decompose_points_locally,
    match_points_locally,
    plan_transition_locally,
)
from sbstudio.model.light_program import LightProgram
from sbstudio.model.trajectory import Trajectory
from sbstudio.model.types import Coordinate3D

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


def _safe_filenames(names: Sequence[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for index, name in enumerate(names, start=1):
        stem = _SAFE_FILENAME_PART.sub("_", name).strip("._") or f"Drone_{index}"
        candidate = stem
        suffix = 2
        while candidate.casefold() in used:
            candidate = f"{stem}_{suffix}"
            suffix += 1
        used.add(candidate.casefold())
        result[name] = f"{candidate}.csv"
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

    This backend deliberately does not claim to generate production-ready
    ``.skyc`` files or perform the licensed server's advanced safety planning.
    """

    def get_limits(self) -> Limits:
        return Limits(features=["offline-design"])

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
        if velocity <= 0:
            raise SkybrushStudioAPIError("landing velocity must be positive")

        target = [(x, y, target_altitude) for x, y, _ in points]
        groups = decompose_points_locally(target, min_distance=min_distance)
        durations = [
            max(0.0, point[2] - target_altitude) / velocity for point in points
        ]
        group_ids = sorted(
            set(groups),
            key=lambda group: min(
                point[2]
                for point, item_group in zip(points, groups)
                if item_group == group
            ),
        )
        group_start: dict[int, float] = {}
        cursor = 0.0
        for group in group_ids:
            group_start[group] = cursor
            cursor += max(
                duration
                for duration, item_group in zip(durations, groups)
                if item_group == group
            ) + max(0.0, spindown_time)
        return [group_start[group] for group in groups], durations

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

    def plan_smart_rth(self, *args, **kwargs):
        raise _unsupported("Smart return-to-home planning")

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
        **kwargs,
    ) -> bytes | None:
        if renderer != "csv":
            raise _unsupported("This export format")
        if renderer_params is not None and not isinstance(renderer_params, dict):
            raise SkybrushStudioAPIError("invalid CSV renderer parameters")

        fps = float((renderer_params or {}).get("fps", 4))
        data = _render_csv_zip(trajectories, lights, fps=fps)
        if output is None:
            return data

        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return None
