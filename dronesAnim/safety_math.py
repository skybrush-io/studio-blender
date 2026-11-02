"""Frame-level drone safety calculations without Blender dependencies."""

from dataclasses import dataclass, field
from math import atan2, cos, degrees, hypot, sin

from .nearest_neighbors import find_proximity_pairs

Point = tuple[float, float, float]


@dataclass
class Snapshot:
    frame: int
    positions: dict[str, Point]
    yaws: dict[str, float]


@dataclass
class Limits:
    proximity: float = 3.0
    proximity_target: str = "ABOVE_MIN_NAV_ALT"
    min_navigation_altitude: float = 2.5
    max_altitude: float = 150.0
    max_velocity_xy: float = 10.0
    max_velocity_z_down: float = 2.0
    max_velocity_z_up: float = 2.0
    max_acceleration: float = 4.0
    max_yaw_rate: float = 30.0
    proximity_enabled: bool = True
    altitude_enabled: bool = True
    velocity_enabled: bool = True
    acceleration_enabled: bool = True
    yaw_rate_enabled: bool = True


@dataclass
class Result:
    frame: int
    drone_count: int
    min_distance: float | None = None
    closest_pair: tuple[str, str] | None = None
    close_pairs: list[tuple[str, str]] = field(default_factory=list)
    min_altitude: float | None = None
    max_altitude: float | None = None
    max_velocity_xy: float | None = None
    max_velocity_z_up: float | None = None
    max_velocity_z_down: float | None = None
    max_acceleration: float | None = None
    max_yaw_rate: float | None = None
    warnings: dict[str, set[str]] = field(default_factory=dict)

    @property
    def warning_count(self) -> int:
        return sum(len(names) for names in self.warnings.values())


def _velocity(current: Snapshot, previous: Snapshot | None, fps: float):
    if previous is None or current.frame != previous.frame + 1:
        return None
    return {
        name: tuple(
            (point[i] - previous.positions[name][i]) * fps for i in range(3)
        )
        for name, point in current.positions.items()
        if name in previous.positions
    }


def _yaw_rate(current: float, previous: float, fps: float) -> float:
    delta = current - previous
    return degrees(abs(atan2(sin(delta), cos(delta)))) * fps


def evaluate_frame(
    current: Snapshot,
    limits: Limits,
    fps: float,
    previous: Snapshot | None = None,
    earlier: Snapshot | None = None,
    *,
    all_pairs: bool = True,
) -> Result:
    result = Result(frame=current.frame, drone_count=len(current.positions))
    if not current.positions:
        return result

    points = current.positions
    result.min_altitude = min(point[2] for point in points.values())
    result.max_altitude = max(point[2] for point in points.values())
    if limits.altitude_enabled:
        result.warnings["altitude"] = {
            name for name, point in points.items() if point[2] >= limits.max_altitude
        }

    candidates = [
        (name, point)
        for name, point in points.items()
        if limits.proximity_target == "ALL"
        or point[2] >= limits.min_navigation_altitude
    ]
    candidates.sort(key=lambda item: item[1][0])
    threshold_sq = limits.proximity**2 if limits.proximity_enabled else 0.0
    closest, result.min_distance, close_pairs = find_proximity_pairs(
        [point for _, point in candidates],
        abs(limits.proximity) if limits.proximity_enabled else 0.0,
        all_pairs=all_pairs,
    )
    if closest is not None:
        first, second = sorted(closest)
        result.closest_pair = (candidates[first][0], candidates[second][0])
        best_sq = sum(
            (candidates[first][1][i] - candidates[second][1][i]) ** 2
            for i in range(3)
        )
        if limits.proximity_enabled and best_sq < threshold_sq:
            result.warnings["proximity"] = set(result.closest_pair)
    result.close_pairs = [
        (candidates[first][0], candidates[second][0])
        for first, second in close_pairs
    ]
    if result.close_pairs:
        result.warnings["proximity"] = {
            name for pair in result.close_pairs for name in pair
        }

    velocities = _velocity(current, previous, fps)
    if velocities is None:
        return result
    result.max_velocity_xy = max(
        (hypot(velocity[0], velocity[1]) for velocity in velocities.values()),
        default=0.0,
    )
    result.max_velocity_z_up = max(
        (max(velocity[2], 0.0) for velocity in velocities.values()), default=0.0
    )
    result.max_velocity_z_down = max(
        (max(-velocity[2], 0.0) for velocity in velocities.values()), default=0.0
    )
    if limits.velocity_enabled:
        result.warnings["velocity"] = {
            name
            for name, velocity in velocities.items()
            if hypot(velocity[0], velocity[1]) > limits.max_velocity_xy
            or velocity[2] > limits.max_velocity_z_up
            or -velocity[2] > limits.max_velocity_z_down
        }
    if limits.altitude_enabled:
        result.warnings["altitude"].update(
            name
            for name, velocity in velocities.items()
            if hypot(velocity[0], velocity[1]) > 0.01
            and points[name][2] < limits.min_navigation_altitude
        )

    rates = {
        name: _yaw_rate(current.yaws[name], previous.yaws[name], fps)
        for name in current.yaws.keys() & previous.yaws.keys()
    }
    result.max_yaw_rate = max(rates.values(), default=0.0)
    if limits.yaw_rate_enabled:
        result.warnings["yaw"] = {
            name
            for name, rate in rates.items()
            if rate > limits.max_yaw_rate
        }

    prior_velocities = _velocity(previous, earlier, fps)
    if prior_velocities is not None:
        accelerations = {
            name: hypot(
                *((velocity[i] - prior_velocities[name][i]) * fps for i in range(3))
            )
            for name, velocity in velocities.items()
            if name in prior_velocities
        }
        result.max_acceleration = max(accelerations.values(), default=0.0)
        if limits.acceleration_enabled:
            result.warnings["acceleration"] = {
                name
                for name, acceleration in accelerations.items()
                if acceleration > limits.max_acceleration
            }
    return result


def warning_messages(result: Result, limits: Limits) -> list[tuple[str, str]]:
    """Return viewport messages grouped by the same categories as drone markers."""
    messages = []
    warnings = result.warnings
    if warnings.get("proximity") and result.min_distance is not None:
        count = (
            f"{len(result.close_pairs)} 对"
            if result.close_pairs
            else f"{len(warnings['proximity'])} 架"
        )
        messages.append(
            (
                "proximity",
                f"距离警告: 最近 {result.min_distance:.2f} m < {limits.proximity:.2f} m ({count})",
            )
        )
    if warnings.get("altitude"):
        messages.append(
            (
                "altitude",
                f"高度警告: {len(warnings['altitude'])} 架, "
                f"范围 {result.min_altitude:.2f} - {result.max_altitude:.2f} m "
                f"(最低导航 {limits.min_navigation_altitude:.2f} m, "
                f"最高 {limits.max_altitude:.2f} m)",
            )
        )
    if warnings.get("velocity"):
        messages.append(
            (
                "velocity",
                f"速度警告: {len(warnings['velocity'])} 架, "
                f"水平 {result.max_velocity_xy:.2f}/{limits.max_velocity_xy:.2f} m/s",
            )
        )
        messages.append(
            (
                "velocity",
                f"  上升 {result.max_velocity_z_up:.2f}/{limits.max_velocity_z_up:.2f}, "
                f"下降 {result.max_velocity_z_down:.2f}/{limits.max_velocity_z_down:.2f} m/s",
            )
        )
    if warnings.get("acceleration"):
        messages.append(
            (
                "acceleration",
                f"加速度警告: {len(warnings['acceleration'])} 架, "
                f"最大 {result.max_acceleration:.2f}/{limits.max_acceleration:.2f} m/s²",
            )
        )
    if warnings.get("yaw"):
        messages.append(
            (
                "yaw",
                f"偏航角速度警告: {len(warnings['yaw'])} 架, "
                f"最大 {result.max_yaw_rate:.2f}/{limits.max_yaw_rate:.2f} 度/秒",
            )
        )
    return messages
