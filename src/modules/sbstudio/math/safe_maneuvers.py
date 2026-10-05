"""Conservative offline landing/RTH for obstacle-free, point-centre paths.

All drones share the same cubic progress in each phase. Relative position is
therefore a line segment in progress space, so separation is minimized over the
*whole* phase, not a set of time samples. Stops between phases are synchronized.
RTH keeps vehicle identity and colours conflicting horizontal routes into height
layers. This is a bounded route family, not a complete or optimal motion planner:
failure to find a route is NOT proof that every possible route is infeasible.

The certificate concerns these generated curves only. It excludes obstacles,
tracking error, downwash, the preceding show, battery/endurance and flight approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite, sqrt

import numpy as np

from .local_planner import _as_point_array

MAX_FRAME = 1_048_574


@dataclass(frozen=True)
class ManeuverLimits:
    min_distance: float
    max_altitude: float
    max_velocity_xy: float
    max_velocity_z: float
    max_acceleration: float

    def validate(self):
        if any(not isfinite(v) or v <= 0 for v in vars(self).values()):
            raise ValueError("Maneuver limits must all be finite and positive")


@dataclass
class SynchronizedManeuver:
    """World positions at shared Bezier endpoints; handles are horizontal.

    For phase i the time control points are frames[i], handles[i][0],
    handles[i][1], frames[i+1]. Position control points are p, p, q, q.
    Coordinates AND time handles have already been rounded to Blender float32.
    """

    positions: np.ndarray
    frames: tuple[int, ...]
    handles: tuple[tuple[float, float], ...]
    fps: float
    phases: tuple[str, ...]
    limits: ManeuverLimits
    minimum_distance: float | None
    layers: int = 1

    @property
    def duration(self) -> float:
        return (self.frames[-1] - self.frames[0]) / self.fps

    def report(self) -> dict:
        return {
            "planner": "skybrush-synchronized-maneuver-v1",
            "scope": "continuous generated synchronized cubic centre paths; endpoint hold",
            "checks": "separation, altitude, speed and acceleration bounds",
            "limits": vars(self.limits),
            "minimum_distance": self.minimum_distance,
            "frames": self.frames,
            "fps": self.fps,
            "phases": self.phases,
            "layers": self.layers,
            "duration_seconds": self.duration,
            "flight_approved": False,
            "not_evaluated": [
                "preceding show and handoff velocity",
                "obstacles and terrain",
                "tracking error and downwash",
                "endurance, firmware and emergency flight-controller RTH",
            ],
        }


def minimum_phase_distance(source, target):
    """Exact pairwise minimum for common monotone progress in [0, 1]."""
    minimum, pair, progress = float("inf"), None, 0.0
    motion = target - source
    for i in range(len(source) - 1):
        relative = source[i] - source[i + 1 :]
        delta = motion[i] - motion[i + 1 :]
        denominator = np.einsum("ij,ij->i", delta, delta)
        fraction = np.clip(
            np.divide(
                -np.einsum("ij,ij->i", relative, delta),
                denominator,
                out=np.zeros_like(denominator),
                where=denominator > 0,
            ),
            0,
            1,
        )
        closest = relative + fraction[:, None] * delta
        distances = np.linalg.norm(closest, axis=1)
        j = int(np.argmin(distances))
        if distances[j] < minimum:
            minimum, pair, progress = (
                float(distances[j]),
                (i, i + j + 1),
                float(fraction[j]),
            )
    return minimum, pair, progress


def _check_phase(source, target, limits, label):
    distance, pair, _ = minimum_phase_distance(source, target)
    # Only numerical round-off is allowed, not an operational spacing exemption.
    if distance + 1e-9 < limits.min_distance:
        assert pair is not None
        raise ValueError(
            f"{label}: drones {pair[0] + 1} and {pair[1] + 1} would be "
            f"{distance:.6g} m apart (required {limits.min_distance:g} m). "
            "No checked route was found; change the layout or route. "
            "Waiting and landed drones are not exempt from separation."
        )
    if max(float(source[:, 2].max()), float(target[:, 2].max())) > limits.max_altitude:
        raise ValueError(f"{label}: required altitude exceeds the configured ceiling")
    return distance


def _points(points):
    points = _as_point_array(points)
    if not len(points):
        raise ValueError("A checked maneuver needs at least one drone")
    # Avoid overflow and coordinates for which float32 metre-level precision is
    # inadequate. These are show-local coordinates, not geographical coordinates.
    if np.any(np.abs(points) > 100_000):
        raise ValueError("Use show-local coordinates within 100000 m of the origin")
    return points.astype(np.float32).astype(float)


def phase_derivative_bounds(source, target, frame_start, frame_end, handles, fps):
    """Conservative analytic bounds, including float32 time-handle rounding.

    t'(u) is a quadratic Bezier with positive control values; its minimum
    is bounded by their minimum. |t''(u)| is bounded by its endpoint values.
    Apply the chain rule to p(u) = p0 + (3u²-2u³)(p1-p0).
    """
    times = np.array([frame_start, *handles, frame_end], dtype=float) / fps
    differences = np.diff(times)
    lower = 3 * float(differences.min())
    if lower <= 0:
        raise ValueError("Frame precision cannot represent this maneuver")
    second = 6 * float(np.max(np.abs(np.diff(differences))))
    delta = target - source
    xy = float(np.max(np.linalg.norm(delta[:, :2], axis=1)))
    z = float(np.max(np.abs(delta[:, 2])))
    distance = float(np.max(np.linalg.norm(delta, axis=1)))
    return (
        1.5 * xy / lower,
        1.5 * z / lower,
        6 * distance / lower**2 + 1.5 * distance * second / lower**3,
    )


def _build_plan(stages, phases, limits, *, fps, start_frame, layers=1, speeds=None):
    limits.validate()
    if not isfinite(fps) or fps < 0.001 or fps > 1000:
        raise ValueError("Frame rate must be finite and between 0.001 and 1000 FPS")
    if not isinstance(start_frame, int) or not -MAX_FRAME < start_frame < MAX_FRAME:
        raise ValueError("Start frame is outside the supported Blender timeline")
    stages = [_points(stage) for stage in stages]
    if any(stage.shape != stages[0].shape for stage in stages):
        raise ValueError("Source and target drone counts must match")
    frames, handles, positions, names = [start_frame], [], [stages[0]], []
    minimum = _check_phase(stages[0], stages[0], limits, "Starting layout")
    for i, (source, target, label) in enumerate(zip(stages, stages[1:], phases)):
        minimum = min(minimum, _check_phase(source, target, limits, label))
        if np.array_equal(source, target):
            continue
        delta = target - source
        xy = float(np.max(np.linalg.norm(delta[:, :2], axis=1)))
        z = float(np.max(np.abs(delta[:, 2])))
        distance = float(np.max(np.linalg.norm(delta, axis=1)))
        velocity_z = (
            min(limits.max_velocity_z, speeds[i]) if speeds else limits.max_velocity_z
        )
        if not isfinite(velocity_z) or velocity_z <= 0:
            raise ValueError("Landing speed must be finite and positive")
        seconds = (
            max(
                1.5 * xy / limits.max_velocity_xy,
                1.5 * z / velocity_z,
                sqrt(6 * distance / limits.max_acceleration),
            )
            * 1.01
        )
        if not isfinite(seconds) or seconds * fps > 2 * MAX_FRAME:
            raise ValueError("Maneuver duration exceeds the supported Blender timeline")
        length = max(3, ceil(seconds * fps))
        while True:
            begin, end = frames[-1], frames[-1] + length
            if end > MAX_FRAME:
                raise ValueError("Maneuver exceeds the supported Blender timeline")
            pair = (
                float(np.float32(begin + length / 3)),
                float(np.float32(begin + 2 * length / 3)),
            )
            bounds = phase_derivative_bounds(source, target, begin, end, pair, fps)
            if all(
                actual <= maximum
                for actual, maximum in zip(
                    bounds,
                    (limits.max_velocity_xy, velocity_z, limits.max_acceleration),
                )
            ):
                break
            length *= 2
        frames.append(end)
        handles.append(pair)
        positions.append(target)
        names.append(label)
    if not names:
        if start_frame + 3 > MAX_FRAME:
            raise ValueError("Maneuver exceeds the supported Blender timeline")
        frames.append(start_frame + 3)
        handles.append((float(start_frame + 1), float(start_frame + 2)))
        positions.append(stages[0])
        names.append("Hold")
    return SynchronizedManeuver(
        np.array(positions),
        tuple(frames),
        tuple(handles),
        fps,
        tuple(names),
        limits,
        minimum if isfinite(minimum) else None,
        layers,
    )


def plan_checked_landing(points, *, target_altitude, limits, fps, start_frame):
    limits.validate()
    source = _points(points)
    if not isfinite(target_altitude):
        raise ValueError("Landing altitude must be finite")
    if np.any(source[:, 2] < target_altitude):
        raise ValueError("Landing target cannot be above a drone's starting altitude")
    target = source.copy()
    target[:, 2] = target_altitude
    _check_phase(_points(target), _points(target), limits, "Landing layout")
    return _build_plan(
        [source, target], ["Landing"], limits, fps=fps, start_frame=start_frame
    )


def _route_layers(source, target, min_distance):
    """DSATUR colouring of horizontal routes that conflict at common progress."""
    n = len(source)
    graph = np.zeros((n, n), dtype=bool)
    xy_source, xy_target = source[:, :2], target[:, :2]
    delta = xy_target - xy_source
    for i in range(n - 1):
        relative = xy_source[i] - xy_source[i + 1 :]
        motion = delta[i] - delta[i + 1 :]
        denom = np.einsum("ij,ij->i", motion, motion)
        progress = np.clip(
            np.divide(
                -np.einsum("ij,ij->i", relative, motion),
                denom,
                out=np.zeros_like(denom),
                where=denom > 0,
            ),
            0,
            1,
        )
        graph[i, i + 1 :] = (
            np.linalg.norm(relative + progress[:, None] * motion, axis=1) < min_distance
        )
    graph |= graph.T
    colors = [-1] * n
    neighbors = [set(np.flatnonzero(row)) for row in graph]
    saturation = [set() for _ in range(n)]
    for _ in range(n):
        node = max(
            (i for i in range(n) if colors[i] < 0),
            key=lambda i: (len(saturation[i]), len(neighbors[i]), -i),
        )
        color = 0
        while color in saturation[node]:
            color += 1
        colors[node] = color
        for other in neighbors[node]:
            saturation[other].add(color)
    return np.asarray(colors)


def plan_checked_rth(
    source,
    target,
    *,
    cruise_altitude,
    limits,
    fps,
    start_frame,
    landing_velocity=None,
    layer_height=0,
):
    """Lift, layered transfer, then descend to each drone's actual target Z.

    Every phase (including climb/descent and stationary drones) is checked.
    No ground exemption, route reassignment or online fallback is performed.
    """
    limits.validate()
    source, target = _points(source), _points(target)
    if source.shape != target.shape:
        raise ValueError("Source and target drone counts must match")
    if not isfinite(cruise_altitude) or not isfinite(layer_height) or layer_height < 0:
        raise ValueError("Cruise altitude and nonnegative layer height must be finite")
    if landing_velocity is not None and (
        not isfinite(landing_velocity) or landing_velocity <= 0
    ):
        raise ValueError("Landing speed must be finite and positive")
    _check_phase(source, source, limits, "Starting layout")
    _check_phase(target, target, limits, "Home layout")
    colors = _route_layers(source, target, limits.min_distance + 0.01)
    base = max(cruise_altitude, float(source[:, 2].max()), float(target[:, 2].max()))
    heights = base + colors * max(limits.min_distance + 0.01, layer_height)
    if float(heights.max()) > limits.max_altitude:
        raise ValueError(
            f"No checked layered route fits the altitude ceiling ({limits.max_altitude:g} m); "
            f"this route needs {int(colors.max()) + 1} layers up to {heights.max():.3f} m. "
            "Change the route/layout; raising a flight limit needs independent review."
        )
    lifted, transferred = source.copy(), target.copy()
    lifted[:, 2] = transferred[:, 2] = heights
    return _build_plan(
        [source, lifted, transferred, target],
        ["Climb to layers", "Layered return", "Final descent"],
        limits,
        fps=fps,
        start_frame=start_frame,
        layers=int(colors.max()) + 1,
        speeds=[
            limits.max_velocity_z,
            limits.max_velocity_z,
            landing_velocity if landing_velocity is not None else limits.max_velocity_z,
        ],
    )
