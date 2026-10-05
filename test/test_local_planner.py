from math import isclose

from sbstudio.math.local_planner import (
    decompose_points_locally,
    estimate_transition_duration,
    match_points_locally,
    plan_transition_locally,
)


def test_match_points_finds_minimum_distance_assignment():
    source = [(0, 0, 0), (10, 0, 0), (20, 0, 0)]
    target = [(19, 0, 0), (1, 0, 0), (11, 0, 0)]

    mapping, clearance = match_points_locally(source, target)

    assert mapping == [2, 0, 1]
    assert clearance is not None
    assert clearance >= 8


def test_match_points_supports_different_formation_sizes():
    mapping, _ = match_points_locally(
        [(0, 0, 0), (10, 0, 0)],
        [(0, 0, 0), (5, 0, 0), (10, 0, 0)],
    )

    assert mapping == [0, None, 1]


def test_decompose_points_separates_all_close_neighbors():
    points = [(0, 0, 0), (0.5, 0, 0), (3, 0, 0), (3.5, 0, 0)]
    groups = decompose_points_locally(points, min_distance=1)

    assert groups[0] != groups[1]
    assert groups[2] != groups[3]
    assert len(set(groups)) == 2


def test_estimate_transition_duration_honors_velocity_and_acceleration():
    # Smoothstep peaks: speed=1.5*d/T, acceleration=6*d/T**2.
    duration = estimate_transition_duration(
        (0, 0, 0),
        (10, 0, 0),
        max_velocity_xy=2,
        max_velocity_z=2,
        max_acceleration=1,
    )

    assert isclose(duration, 60**0.5)


def test_vertical_transition_matches_analytic_smoothstep_bound():
    # max(1.5 * 6 / 2, sqrt(6 * 6 / 2)) = 4.5 seconds.
    duration = estimate_transition_duration(
        (0, 0, 0),
        (0, 0, 6),
        max_velocity_xy=4,
        max_velocity_z=2,
        max_acceleration=2,
    )
    assert isclose(duration, 4.5)


def test_smoothstep_derivatives_respect_limits():
    for distance in (0.001, 1, 6, 100):
        duration = estimate_transition_duration(
            (0, 0, 0),
            (distance, 0, distance),
            max_velocity_xy=4,
            max_velocity_z=2,
            max_acceleration=2,
        )
        for step in range(101):
            u = step / 100
            assert distance * 6 * u * (1 - u) / duration <= 2 + 1e-10
            assert abs(distance * (6 - 12 * u) / duration**2) <= 2 + 1e-10


def test_plan_transition_uses_target_to_source_mapping():
    plan = plan_transition_locally(
        [(0, 0, 0), (10, 0, 0)],
        [(9, 0, 0), (1, 0, 0)],
        max_velocity_xy=2,
        max_velocity_z=2,
        max_acceleration=1,
    )

    assert plan.mapping == [1, 0]
    assert plan.start_times == [0, 0]
    assert plan.total_duration > 0
