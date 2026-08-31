"""Small, dependency-free-from-the-server planning helpers for offline design.

The algorithms in this module intentionally cover only the operations needed to
build and preview a show in Blender.  They are not a replacement for the
production-grade validation and export pipeline in Skybrush Studio Server.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from math import hypot, inf, sqrt

import numpy as np

from sbstudio.model.types import Coordinate3D

Mapping = Sequence[int | None]

__all__ = (
    "decompose_points_locally",
    "estimate_transition_duration",
    "LocalTransitionPlan",
    "match_points_locally",
    "plan_transition_locally",
)


@dataclass
class LocalTransitionPlan:
    """Subset of the Studio transition-plan response used by the add-on."""

    start_times: list[float] = field(default_factory=list)
    durations: list[float] = field(default_factory=list)
    mapping: Mapping | None = None
    clearance: float | None = None

    @classmethod
    def empty(cls) -> LocalTransitionPlan:
        return cls(mapping=[])

    @property
    def total_duration(self) -> float:
        return (
            max(
                start_time + duration
                for start_time, duration in zip(self.start_times, self.durations)
            )
            if self.start_times and self.durations
            else 0.0
        )


def _as_point_array(points: Sequence[Coordinate3D]) -> np.ndarray:
    result = np.asarray(points, dtype=float)
    if len(points) == 0:
        return np.empty((0, 3), dtype=float)
    if result.ndim != 2 or result.shape[1] != 3:
        raise ValueError("points must be a sequence of three-dimensional coordinates")
    if not np.all(np.isfinite(result)):
        raise ValueError("point coordinates must be finite")
    return result


def _minimum_cost_assignment(cost: np.ndarray) -> np.ndarray:
    """Assign every row to a unique column using the Hungarian algorithm.

    The input must have at most as many rows as columns.  The implementation is
    vectorized in the inner loop so a 500-by-500 formation remains practical in
    Blender without adding SciPy as a bundled dependency.
    """

    num_rows, num_columns = cost.shape
    if num_rows > num_columns:
        raise ValueError("assignment matrix must not have more rows than columns")
    if num_rows == 0:
        return np.empty(0, dtype=int)

    row_potential = np.zeros(num_rows + 1, dtype=float)
    column_potential = np.zeros(num_columns + 1, dtype=float)
    assigned_row = np.zeros(num_columns + 1, dtype=int)
    previous_column = np.zeros(num_columns + 1, dtype=int)

    for row in range(1, num_rows + 1):
        assigned_row[0] = row
        minimum_reduced_cost = np.full(num_columns + 1, inf, dtype=float)
        used = np.zeros(num_columns + 1, dtype=bool)
        column = 0

        while True:
            used[column] = True
            current_row = assigned_row[column]
            unused_columns = np.flatnonzero(~used[1:]) + 1
            reduced_cost = (
                cost[current_row - 1, unused_columns - 1]
                - row_potential[current_row]
                - column_potential[unused_columns]
            )

            improves = reduced_cost < minimum_reduced_cost[unused_columns]
            improved_columns = unused_columns[improves]
            minimum_reduced_cost[improved_columns] = reduced_cost[improves]
            previous_column[improved_columns] = column

            best_offset = int(np.argmin(minimum_reduced_cost[unused_columns]))
            delta = minimum_reduced_cost[unused_columns[best_offset]]
            next_column = int(unused_columns[best_offset])

            used_columns = np.flatnonzero(used)
            row_potential[assigned_row[used_columns]] += delta
            column_potential[used_columns] -= delta
            minimum_reduced_cost[unused_columns] -= delta

            column = next_column
            if assigned_row[column] == 0:
                break

        while True:
            predecessor = previous_column[column]
            assigned_row[column] = assigned_row[predecessor]
            column = predecessor
            if column == 0:
                break

    result = np.full(num_rows, -1, dtype=int)
    for column in range(1, num_columns + 1):
        row = assigned_row[column]
        if row:
            result[row - 1] = column - 1
    return result


def _calculate_clearance(
    source: np.ndarray,
    target: np.ndarray,
    target_to_source: Mapping,
    *,
    radius: float,
) -> float | None:
    assignments = [
        (source_index, target_index)
        for target_index, source_index in enumerate(target_to_source)
        if source_index is not None
    ]
    if len(assignments) < 2:
        return None

    starts = np.asarray([source[i] for i, _ in assignments])
    ends = np.asarray([target[j] for _, j in assignments])
    velocities = ends - starts
    minimum_distance_squared = inf

    for index in range(len(assignments) - 1):
        relative_start = starts[index] - starts[index + 1 :]
        relative_velocity = velocities[index] - velocities[index + 1 :]
        denominator = np.einsum("ij,ij->i", relative_velocity, relative_velocity)
        numerator = -np.einsum("ij,ij->i", relative_start, relative_velocity)
        times = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator),
            where=denominator > 0,
        )
        times = np.clip(times, 0.0, 1.0)
        closest = relative_start + times[:, None] * relative_velocity
        distances_squared = np.einsum("ij,ij->i", closest, closest)
        if len(distances_squared):
            minimum_distance_squared = min(
                minimum_distance_squared, float(np.min(distances_squared))
            )

    return sqrt(minimum_distance_squared) - 2 * max(0.0, float(radius))


def match_points_locally(
    source: Sequence[Coordinate3D],
    target: Sequence[Coordinate3D],
    *,
    radius: float = 0,
) -> tuple[list[int | None], float | None]:
    """Return a minimum-total-distance mapping from targets to sources.

    The mapping follows the Studio API convention: item ``i`` is the source
    point assigned to target ``i``.  Excess targets are left unmatched.
    """

    source_array = _as_point_array(source)
    target_array = _as_point_array(target)
    num_sources = len(source_array)
    num_targets = len(target_array)
    result: list[int | None] = [None] * num_targets

    if not num_sources or not num_targets:
        return result, None

    squared_distances = np.sum(
        (source_array[:, None, :] - target_array[None, :, :]) ** 2,
        axis=2,
    )

    if num_sources <= num_targets:
        source_to_target = _minimum_cost_assignment(squared_distances)
        for source_index, target_index in enumerate(source_to_target):
            result[int(target_index)] = source_index
    else:
        target_to_source = _minimum_cost_assignment(squared_distances.T)
        result = [int(source_index) for source_index in target_to_source]

    clearance = _calculate_clearance(
        source_array,
        target_array,
        result,
        radius=radius,
    )
    return result, clearance


def decompose_points_locally(
    points: Sequence[Coordinate3D], *, min_distance: float
) -> list[int]:
    """Color the proximity graph so points in one group are safely separated."""

    point_array = _as_point_array(points)
    count = len(point_array)
    if count == 0:
        return []
    if min_distance <= 0:
        return [0] * count

    offsets = point_array[:, None, :] - point_array[None, :, :]
    distances_squared = np.einsum("ijk,ijk->ij", offsets, offsets)
    adjacent = distances_squared < float(min_distance) ** 2
    np.fill_diagonal(adjacent, False)

    colors = [-1] * count
    degrees = np.count_nonzero(adjacent, axis=1)

    # DSATUR generally produces fewer takeoff/landing layers than a simple
    # index-ordered greedy coloring while remaining deterministic.
    for _ in range(count):
        uncolored = [index for index, color in enumerate(colors) if color < 0]

        def priority(index: int) -> tuple[int, int, int]:
            neighbor_colors = {
                colors[neighbor]
                for neighbor in np.flatnonzero(adjacent[index])
                if colors[neighbor] >= 0
            }
            return len(neighbor_colors), int(degrees[index]), -index

        selected = max(uncolored, key=priority)
        forbidden = {
            colors[neighbor]
            for neighbor in np.flatnonzero(adjacent[selected])
            if colors[neighbor] >= 0
        }
        color = 0
        while color in forbidden:
            color += 1
        colors[selected] = color

    return colors


def estimate_transition_duration(
    source: Coordinate3D,
    target: Coordinate3D,
    *,
    max_velocity_xy: float,
    max_velocity_z: float,
    max_acceleration: float,
    max_velocity_z_up: float | None = None,
) -> float:
    """Estimate a conservative point-to-point duration with speed/accel limits."""

    if max_velocity_xy <= 0 or max_velocity_z <= 0 or max_acceleration <= 0:
        raise ValueError("velocity and acceleration limits must be positive")

    dx = float(target[0]) - float(source[0])
    dy = float(target[1]) - float(source[1])
    dz = float(target[2]) - float(source[2])
    vertical_velocity = (
        max_velocity_z_up
        if dz > 0 and max_velocity_z_up is not None
        else max_velocity_z
    )
    if vertical_velocity <= 0:
        raise ValueError("vertical velocity limit must be positive")

    def duration_for(distance: float, velocity: float) -> float:
        distance = abs(distance)
        ramp_distance = velocity * velocity / max_acceleration
        if distance <= ramp_distance:
            return 2 * sqrt(distance / max_acceleration)
        return distance / velocity + velocity / max_acceleration

    return max(
        duration_for(hypot(dx, dy), max_velocity_xy),
        duration_for(dz, vertical_velocity),
    )


def plan_transition_locally(
    source: Sequence[Coordinate3D],
    target: Sequence[Coordinate3D],
    *,
    max_velocity_xy: float,
    max_velocity_z: float,
    max_acceleration: float,
    max_velocity_z_up: float | None = None,
) -> LocalTransitionPlan:
    if len(source) == 0 or len(target) == 0:
        return LocalTransitionPlan.empty()

    mapping, clearance = match_points_locally(source, target)
    durations = [
        (
            estimate_transition_duration(
                source[source_index],
                target[target_index],
                max_velocity_xy=max_velocity_xy,
                max_velocity_z=max_velocity_z,
                max_acceleration=max_acceleration,
                max_velocity_z_up=max_velocity_z_up,
            )
            if source_index is not None
            else 0.0
        )
        for target_index, source_index in enumerate(mapping)
    ]
    return LocalTransitionPlan(
        start_times=[0.0] * len(target),
        durations=durations,
        mapping=mapping,
        clearance=clearance,
    )
