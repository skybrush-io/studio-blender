"""Continuous checks of exported piecewise-linear trajectories, without Blender."""

from collections.abc import Callable, Mapping, Sequence
from math import isclose, isfinite

import numpy as np

from .motion_diagnostics import acceleration_diagnostics, normalize_phases, phase_at
from .pairwise_workspace import PairwiseWorkspace


def validate_trajectories(
    trajectories: Mapping[str, Sequence[Sequence[float]]],
    *,
    min_distance: float = 3,
    max_altitude: float = 150,
    max_velocity_xy: float = 8,
    max_velocity_z: float = 3,
    max_velocity_z_up: float | None = None,
    ground_clearance: float = 0.1,
    max_acceleration: float = 4,
    show_segments: Mapping[str, Sequence[float]] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict:
    """Check [time,x,y,z] paths continuously, holding endpoints outside their span.

    A union of all timestamps partitions the show into linear intervals. Pairwise
    relative motion is linear on each interval; minimizing its squared norm is
    exact for this representation, including collisions between keyframes.
    This does not validate the unsampled Blender animation or finite acceleration
    at polyline corners. No flight-readiness verdict is issued.
    """
    limits = (min_distance, max_altitude, max_velocity_xy, max_velocity_z)
    if any(not isfinite(v) or v < 0 for v in limits):
        raise ValueError("validation limits must be finite and nonnegative")
    up_limit = max_velocity_z if max_velocity_z_up is None else max_velocity_z_up
    if not isfinite(up_limit) or up_limit < 0:
        raise ValueError("ascent speed limit must be finite and nonnegative")
    if not trajectories:
        raise ValueError("cannot validate an empty show")
    if not isfinite(ground_clearance) or ground_clearance <= 0:
        raise ValueError("ground clearance must be finite and positive")
    names = list(trajectories)
    paths = []
    for name in names:
        path = np.asarray(trajectories[name], dtype=float)
        if path.ndim != 2 or path.shape[1] != 4 or not len(path):
            raise ValueError(f"{name}: expected nonempty [time,x,y,z] path")
        if not np.isfinite(path).all() or (path[:, 0] < 0).any():
            raise ValueError(f"{name}: values must be finite and times nonnegative")
        if (np.diff(path[:, 0]) <= 0).any():
            raise ValueError(f"{name}: timestamps must strictly increase")
        paths.append(path)
    # Split at altitude threshold crossings so a pair cannot change category
    # inside an interval. Initial height is an explicit heuristic, not telemetry.
    ground_heights = np.array([p[0, 3] for p in paths])
    crossings = []
    for path, height in zip(paths, ground_heights):
        z = path[:, 3] - height - ground_clearance
        for i in np.flatnonzero(z[:-1] * z[1:] < 0):
            fraction = -z[i] / (z[i + 1] - z[i])
            crossings.append(path[i, 0] + fraction * (path[i + 1, 0] - path[i, 0]))
    phases, phase_issues = normalize_phases(show_segments)
    first_time = min(p[0, 0] for p in paths)
    last_time = max(p[-1, 0] for p in paths)
    boundaries = [
        t
        for start, end, _ in phases
        for t in (start, end)
        if first_time < t < last_time
    ]
    times = np.unique(
        np.concatenate([*[p[:, 0] for p in paths], crossings, boundaries])
    )
    acceleration = acceleration_diagnostics(names, paths, max_acceleration, phases)
    storyboard_minima: dict[str, dict] = {}
    # O(N*T) positions, O(N**2) pair workspace, not O(N**2*T).
    positions = np.stack(
        [
            np.stack(
                [np.interp(times, p[:, 0], p[:, axis]) for axis in (1, 2, 3)], axis=1
            )
            for p in paths
        ]
    )
    workspace = PairwiseWorkspace(len(names))
    pair_i, pair_j = workspace.pair_i, workspace.pair_j
    closest = None
    minimum_squared = float("inf")
    max_xy = max_up = max_down = 0.0
    peaks = {kind: {} for kind in ("horizontal_speed", "ascent_speed", "descent_speed")}
    phase_minima = dict.fromkeys(("both_near_initial_height", "airborne_or_mixed"))
    initial_layout: dict | None = None
    # Use original per-drone intervals for velocity diagnostics, avoiding tiny
    # artificial intervals from other drones' threshold crossings.
    for name, path in zip(names, paths):
        if len(path) < 2:
            continue
        velocity = np.diff(path[:, 1:], axis=0) / np.diff(path[:, 0])[:, None]
        for kind, values in (
            ("horizontal_speed", np.linalg.norm(velocity[:, :2], axis=1)),
            ("ascent_speed", np.maximum(velocity[:, 2], 0)),
            ("descent_speed", np.maximum(-velocity[:, 2], 0)),
        ):
            index = int(np.argmax(values))
            peaks[kind][name] = {
                "drone": name,
                "value": float(values[index]),
                "time_start": float(path[index, 0]),
                "time_end": float(path[index + 1, 0]),
            }
    max_xy, max_up, max_down = (
        max((r["value"] for r in peaks[kind].values()), default=0.0)
        for kind in ("horizontal_speed", "ascent_speed", "descent_speed")
    )
    for index, time in enumerate(times):
        if on_progress is not None:
            on_progress(index, len(times))
        start = positions[:, index, :]
        if index + 1 < len(times):
            dt = times[index + 1] - time
            squared, offset = workspace.evaluate(start, positions[:, index + 1, :])
        else:
            dt = 0.0
            squared, offset = workspace.evaluate(start)
        if len(pair_i):
            best = int(np.argmin(squared))
            if squared[best] < minimum_squared:
                minimum_squared = float(squared[best])
                closest = {
                    "drones": [names[pair_i[best]], names[pair_j[best]]],
                    "time": float(time + offset[best] * dt),
                }
            phase = phase_at(float(time + dt / 2), phases)
            candidate_distance = float(np.sqrt(squared[best]))
            if (
                phase not in storyboard_minima
                or candidate_distance < storyboard_minima[phase]["minimum_distance"]
            ):
                storyboard_minima[phase] = {
                    "minimum_distance": candidate_distance,
                    "drones": [names[pair_i[best]], names[pair_j[best]]],
                    "time": float(time + offset[best] * dt),
                }
            if index == 0:
                initial_squared = np.sum((start[pair_i] - start[pair_j]) ** 2, axis=1)
                initial_best = int(np.argmin(initial_squared))
                initial_layout = {
                    "minimum_distance": float(np.sqrt(initial_squared[initial_best])),
                    "drones": [
                        names[pair_i[initial_best]],
                        names[pair_j[initial_best]],
                    ],
                    "time": float(time),
                }
            midpoint = (start + positions[:, index + 1, :]) / 2 if dt else start
            above = midpoint[:, 2] > ground_heights + ground_clearance
            airborne = above[pair_i] | above[pair_j]
            for phase, mask in (
                ("airborne_or_mixed", airborne),
                ("both_near_initial_height", ~airborne),
            ):
                indices = np.flatnonzero(mask)
                if not len(indices):
                    continue
                winner = int(indices[np.argmin(squared[indices])])
                phase_distance = float(np.sqrt(squared[winner]))
                previous = phase_minima[phase]
                if previous is None or phase_distance < previous["minimum_distance"]:
                    phase_minima[phase] = {
                        "minimum_distance": phase_distance,
                        "drones": [names[pair_i[winner]], names[pair_j[winner]]],
                        "time": float(time + offset[winner] * dt),
                    }
    if on_progress is not None:
        on_progress(len(times), len(times))
    distance = float(np.sqrt(minimum_squared)) if closest else None
    altitude = float(positions[:, :, 2].max())

    def at_most(value: float, limit: float) -> bool:
        return value <= limit or isclose(value, limit, rel_tol=1e-12, abs_tol=1e-9)

    checks = {
        "separation": distance is None or at_most(min_distance, distance),
        "altitude": at_most(altitude, max_altitude),
        "horizontal_speed": at_most(max_xy, max_velocity_xy),
        "ascent_speed": at_most(max_up, up_limit),
        "descent_speed": at_most(max_down, max_velocity_z),
    }
    speed_limits = {
        "horizontal_speed": max_velocity_xy,
        "ascent_speed": up_limit,
        "descent_speed": max_velocity_z,
    }
    for records in peaks.values():
        for record in records.values():
            record["phase_at_interval_midpoint"] = phase_at(
                (record["time_start"] + record["time_end"]) / 2, phases
            )
    violations = [
        {"check": kind, "limit": speed_limits[kind], **record}
        for kind, records in peaks.items()
        for record in records.values()
        if not at_most(record["value"], speed_limits[kind])
    ]
    for record in (initial_layout, *phase_minima.values(), *storyboard_minima.values()):
        if record is not None:
            record["meets_spacing_limit"] = at_most(
                min_distance, record["minimum_distance"]
            )
    return {
        "version": 3,
        "scope": "continuous piecewise-linear exported positions; endpoint hold",
        "drone_count": len(names),
        "time_range": [float(times[0]), float(times[-1])],
        "limits": dict(
            zip(
                ("min_distance", "max_altitude", "max_velocity_xy", "max_velocity_z"),
                limits,
            ),
            max_velocity_z_up=up_limit,
        ),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "minimum_distance": distance,
        "closest_pair": closest,
        "maximum_altitude": altitude,
        "maximum_horizontal_speed": max_xy,
        "maximum_ascent_speed": max_up,
        "maximum_descent_speed": max_down,
        "speed_peaks": {
            kind: max(records.values(), key=lambda r: r["value"]) if records else None
            for kind, records in peaks.items()
        },
        "speed_violations": violations,
        "speed_violation_scope": "worst interval per drone per speed check; times in exported-show seconds",
        "initial_layout": initial_layout,
        "separation_by_height": phase_minima,
        "height_classification": {
            "method": "height above each drone's first exported position",
            "clearance_m": ground_clearance,
            "airborne_or_mixed": "at least one drone above threshold; includes interval boundaries",
            "limitations": "initial heights are assumed ground; unsuitable for clips starting airborne; no separation violations are exempted",
        },
        "storyboard_phases": {
            "source": "authored storyboard purposes; not measured flight state",
            "intervals": [
                {"name": name, "start": start, "end": end}
                for start, end, name in phases
            ],
            "issues": phase_issues,
            "status": "available" if phases else "unavailable",
            "limitations": "gaps remain unclassified; interval minima include boundary points; no spacing exemptions",
        },
        "separation_by_storyboard_phase": storyboard_minima,
        "acceleration_estimates": acceleration,
        "diagnostic_warnings": (
            ["acceleration_estimate_exceeds_limit"]
            if acceleration["violations"]
            else []
        ),
        "not_evaluated": [
            "flight-phase exemptions and minimum navigation altitude",
            "acceleration at polyline corners",
            "unsampled Blender motion",
            "yaw rate",
            "downwash",
            "vehicle tracking error",
            "flight readiness",
        ],
    }
