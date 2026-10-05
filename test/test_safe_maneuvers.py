from dataclasses import replace
from time import perf_counter

import numpy as np
import pytest
from numpy.polynomial import Polynomial
from sbstudio.math.safe_maneuvers import (
    MAX_FRAME,
    ManeuverLimits,
    minimum_phase_distance,
    phase_derivative_bounds,
    plan_checked_landing,
    plan_checked_rth,
)

LIMITS = ManeuverLimits(3, 150, 4, 2, 4)
OPTIONS = {"limits": LIMITS, "fps": 24 / 1.001, "start_frame": 121}


def rth(source, target, **kwargs):
    return plan_checked_rth(
        source, target, **(dict(OPTIONS, cruise_altitude=20) | kwargs)
    )


def independent_cubic_minimum(source, target):
    """Polynomial stationary roots, independent of the planner's projection."""
    progress = Polynomial([0, 0, 3, -2])
    result = float("inf")
    for i in range(len(source)):
        for j in range(i):
            delta = (target[i] - source[i]) - (target[j] - source[j])
            separation = source[i] - source[j]
            squared = sum(
                (Polynomial([s]) + progress * d) ** 2 for s, d in zip(separation, delta)
            )
            candidates = [0, 1] + [
                float(root.real)
                for root in squared.deriv().roots()
                if abs(root.imag) < 1e-7 and 0 < root.real < 1
            ]
            result = min(result, sqrt_nonnegative(min(squared(u) for u in candidates)))
    return result


def sqrt_nonnegative(value):
    return np.sqrt(max(0, value))


def verify(plan, independent=True):
    assert all(a < b for a, b in zip(plan.frames, plan.frames[1:]))
    assert np.isfinite(plan.positions).all()
    assert plan.positions[:, :, 2].max() <= plan.limits.max_altitude
    for i, (source, target) in enumerate(zip(plan.positions, plan.positions[1:])):
        bounds = phase_derivative_bounds(
            source, target, *plan.frames[i : i + 2], plan.handles[i], plan.fps
        )
        assert np.all(
            np.array(bounds)
            <= [
                plan.limits.max_velocity_xy,
                plan.limits.max_velocity_z,
                plan.limits.max_acceleration,
            ]
        )
        if independent:
            assert (
                independent_cubic_minimum(source, target)
                >= plan.limits.min_distance - 1e-7
            )
    assert plan.report()["flight_approved"] is False


@pytest.mark.parametrize("field", list(vars(LIMITS)))
@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_invalid_limits_fail_closed(field, value):
    with pytest.raises(ValueError, match="finite and positive"):
        rth([(0, 0, 10)], [(0, 0, 0)], limits=replace(LIMITS, **{field: value}))


@pytest.mark.parametrize(
    "points",
    [[], [(0, 0)], [(0, 0, float("nan"))], [(float("inf"), 0, 0)], [(1e10, 0, 0)]],
)
def test_invalid_source_rejected(points):
    with pytest.raises(ValueError):
        rth(points, [(0, 0, 0)])


@pytest.mark.parametrize(
    "option,value",
    [
        ("cruise_altitude", float("nan")),
        ("layer_height", -1),
        ("landing_velocity", 0),
        ("landing_velocity", float("nan")),
        ("fps", 0),
        ("fps", 1e-300),
        ("fps", float("inf")),
        ("fps", 1e300),
        ("start_frame", MAX_FRAME),
        ("start_frame", 1.5),
    ],
)
def test_invalid_planning_controls(option, value):
    with pytest.raises(ValueError):
        rth([(0, 0, 10)], [(0, 0, 0)], **{option: value})


def test_counts_cannot_be_silently_truncated():
    with pytest.raises(ValueError, match="counts"):
        rth([(0, 0, 10), (4, 0, 10)], [(0, 0, 0)])


@pytest.mark.parametrize("near_end", ["source", "target"])
def test_waiting_and_landed_drones_are_not_exempt(near_end):
    source, target = [(0, 0, 10), (4, 0, 10)], [(0, 0, 0), (4, 0, 0)]
    (source if near_end == "source" else target)[1] = (
        0.5,
        0,
        10 if near_end == "source" else 0,
    )
    with pytest.raises(ValueError, match="not exempt"):
        rth(source, target)


def test_head_on_swap_gets_different_layers_and_preserves_identity():
    source, target = [(0, 0, 10), (10, 0, 10)], [(10, 0, 2), (0, 0, 5)]
    plan = rth(source, target, landing_velocity=0.5)
    assert plan.layers == 2
    np.testing.assert_array_equal(plan.positions[0], source)
    np.testing.assert_array_equal(plan.positions[-1], target)
    verify(plan)
    last = phase_derivative_bounds(
        *plan.positions[-2:], *plan.frames[-2:], plan.handles[-1], plan.fps
    )
    assert last[1] <= 0.5


def test_vertical_order_reversal_is_rejected_even_with_separated_endpoints():
    with pytest.raises(ValueError, match="Final descent"):
        rth([(0, 0, 10), (0, 0, 14)], [(0, 0, 4), (0, 0, 0)])


def test_climb_collision_with_waiting_drone_is_rejected():
    with pytest.raises(ValueError, match="Climb to layers"):
        rth([(0, 0, 14), (0, 0, 10)], [(0, 0, 0), (4, 0, 0)])


def test_layer_ceiling_failure_never_returns_partial_plan():
    with pytest.raises(ValueError, match="altitude ceiling"):
        rth(
            [(0, 0, 10), (10, 0, 10)],
            [(10, 0, 0), (0, 0, 0)],
            limits=replace(LIMITS, max_altitude=22),
        )


def test_tiny_speed_and_late_start_fail_without_infinite_schedule():
    with pytest.raises(ValueError, match="timeline"):
        rth([(0, 0, 10)], [(0, 0, 0)], limits=replace(LIMITS, max_velocity_z=1e-300))
    with pytest.raises(ValueError, match="timeline"):
        rth([(0, 0, 10)], [(0, 0, 0)], start_frame=MAX_FRAME - 1)


def test_single_drone_noop_and_negative_start_frames():
    plan = rth([(0, 0, 20)], [(0, 0, 20)], start_frame=-120)
    assert plan.minimum_distance is None
    assert plan.phases == ("Hold",)
    verify(plan)


def test_landing_has_eased_peak_speed_not_average_speed():
    points = [(0, 0, 10), (4, 0, 4), (0, 4, 0)]
    plan = plan_checked_landing(points, target_altitude=0, **OPTIONS)
    assert plan.duration >= 1.5 * 10 / LIMITS.max_velocity_z
    np.testing.assert_array_equal(plan.positions[:, 2], [[0, 4, 0], [0, 4, 0]])
    verify(plan)


@pytest.mark.parametrize("target", [11, float("nan"), float("inf")])
def test_invalid_or_upward_landing(target):
    with pytest.raises(ValueError):
        plan_checked_landing([(0, 0, 10)], target_altitude=target, **OPTIONS)


def test_close_touchdown_cannot_be_fixed_by_vertical_staggering():
    with pytest.raises(ValueError, match="Landing layout"):
        plan_checked_landing([(0, 0, 10), (0.5, 0, 15)], target_altitude=0, **OPTIONS)


def test_float32_time_handles_and_large_frame_numbers_are_bounded():
    plan = rth(
        [(0, 0, 10), (4, 0, 10)],
        [(0, 0, 0), (4, 0, 0)],
        start_frame=800001,
        fps=29.97002997,
    )
    assert all(float(np.float32(v)) == v for handles in plan.handles for v in handles)
    verify(plan)


def test_between_endpoint_collision_is_detected_analytically():
    a = np.array([(0, 0, 0), (10, 0, 0)], dtype=float)
    b = a[::-1].copy()
    assert minimum_phase_distance(a, b) == (0, (0, 1), 0.5)


def test_seeded_permutations_against_independent_polynomial_check():
    random = np.random.default_rng(501000)
    points = np.array(
        [(i * 4, j * 4, 10) for i in range(3) for j in range(3)], dtype=float
    )
    for _ in range(20):
        target = points[random.permutation(9)].copy()
        target[:, 2] = random.uniform(0, 4, 9)
        verify(rth(points, target))


@pytest.mark.parametrize("count", [100, 500])
def test_large_fleet_translation_and_adversarial_adjacent_swaps(count):
    source = np.array(
        [(i % 20 * 4, i // 20 * 4, 10) for i in range(count)], dtype=float
    )
    translation = source + [20, 0, -10]
    started = perf_counter()
    for target in (
        translation,
        source[np.arange(count).reshape(-1, 2)[:, ::-1].ravel()] - [0, 0, 10],
    ):
        plan = rth(source, target)
        verify(plan, independent=False)
        for a, b in zip(plan.positions, plan.positions[1:]):
            # Independent dense pairwise samples for the large stress case.
            for progress in np.linspace(0, 1, 11):
                p = a + (b - a) * progress
                distances = np.linalg.norm(p[:, None] - p[None, :], axis=2)
                np.fill_diagonal(distances, np.inf)
                assert distances.min() >= LIMITS.min_distance - 1e-7
    print(f"{count}-drone landing/RTH stress: {perf_counter() - started:.3f}s")


def test_500_way_crossing_over_capacity_is_rejected():
    angle = np.arange(500) * (2 * np.pi / 500)
    source = np.column_stack(
        [300 * np.cos(angle), 300 * np.sin(angle), np.full(500, 10)]
    )
    target = source * [-1, -1, 0]
    with pytest.raises(ValueError, match="altitude ceiling"):
        rth(source, target)
