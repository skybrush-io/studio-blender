import pytest
from sbstudio.math.local_planner import decompose_points_locally, plan_landing_locally


@pytest.mark.parametrize("distance", [-1, float("nan"), float("inf")])
def test_invalid_separation_rejected_even_for_empty_input(distance):
    with pytest.raises(ValueError):
        decompose_points_locally([], min_distance=distance)


@pytest.mark.parametrize(
    "field,value",
    [
        ("velocity", 0),
        ("velocity", -1),
        ("velocity", float("nan")),
        ("velocity", float("inf")),
        ("spindown_time", -1),
        ("spindown_time", float("nan")),
        ("target_altitude", float("inf")),
        ("min_distance", float("nan")),
    ],
)
def test_invalid_landing_parameters(field, value):
    options = {"velocity": 2, "min_distance": 3}
    options[field] = value
    with pytest.raises(ValueError):
        plan_landing_locally([(0, 0, 10)], **options)


def test_nan_altitude_not_lost_when_projecting_onto_ground():
    with pytest.raises(ValueError, match="coordinates"):
        plan_landing_locally([(0, 0, float("nan"))], velocity=2, min_distance=3)


def test_landing_cannot_silently_schedule_ascent_as_zero_duration():
    with pytest.raises(ValueError, match="above"):
        plan_landing_locally([(0, 0, 1)], velocity=2, min_distance=3, target_altitude=2)


def test_empty_landing():
    assert plan_landing_locally([], velocity=2, min_distance=3) == ([], [])


def test_spindown_does_not_exempt_close_landing_slots():
    with pytest.raises(ValueError, match="landed drones are not exempt"):
        plan_landing_locally(
            [(0, 0, 10), (0.5, 0, 4)], velocity=2, min_distance=3, spindown_time=5
        )


def test_separated_drones_can_land_together():
    assert plan_landing_locally(
        [(0, 0, 10), (4, 0, 4)], velocity=2, min_distance=3
    ) == ([0, 0], [5, 2])
