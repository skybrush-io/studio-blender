import pytest
from sbstudio.math.trajectory_validation import validate_trajectories


def test_detects_collision_between_frames():
    result = validate_trajectories(
        {
            "A": [[0, -5, 0, 0], [10, 5, 0, 0]],
            "B": [[0, 5, 0, 0], [10, -5, 0, 0]],
        }
    )
    assert result["minimum_distance"] == 0
    assert result["closest_pair"] == {"drones": ["A", "B"], "time": 5}
    assert result["failed_checks"] == ["separation"]


def test_merges_asynchronous_timestamps_and_holds_endpoints():
    result = validate_trajectories(
        {
            "A": [[0, 0, 0, 0]],
            "B": [[2, -5, 0, 0], [4, 5, 0, 0]],
        }
    )
    assert result["closest_pair"]["time"] == 3


def test_checks_directional_speed_and_altitude():
    result = validate_trajectories(
        {
            "A": [[0, 0, 0, 0], [1, 9, 0, 6], [2, 9, 0, 0]],
        },
        max_altitude=5,
        max_velocity_z_up=7,
    )
    assert set(result["failed_checks"]) == {
        "horizontal_speed",
        "altitude",
        "descent_speed",
    }
    assert result["minimum_distance"] is None


def test_500_drone_parallel_fleet():
    result = validate_trajectories(
        {str(i): [[0, i * 4, 0, 0], [10, i * 4, 0, 10]] for i in range(500)}
    )
    assert result["drone_count"] == 500
    assert result["minimum_distance"] == 4
    assert result["failed_checks"] == []
    assert "flight readiness" in result["not_evaluated"]


def test_threshold_tolerates_roundoff_but_not_millimeter_violation():
    paths = {"A": [[0, 0, 0, 0]], "B": [[0, 4 - 1e-14, 0, 0]]}
    assert validate_trajectories(paths, min_distance=4)["checks"]["separation"]
    paths["B"][0][1] = 3.999
    assert not validate_trajectories(paths, min_distance=4)["checks"]["separation"]


def test_speed_violations_identify_drone_and_interval():
    report = validate_trajectories(
        {
            "slow": [[0, 0, 0, 0], [2, 0, 0, 2]],
            "fast": [[0, 5, 0, 0], [1, 5, 0, 4], [2, 5, 0, 0]],
        },
        max_velocity_z=2,
    )
    assert report["speed_peaks"]["ascent_speed"] == {
        "drone": "fast",
        "value": 4,
        "time_start": 0,
        "time_end": 1,
        "phase_at_interval_midpoint": "unclassified",
    }
    assert {v["drone"] for v in report["speed_violations"]} == {"fast"}
    assert {v["check"] for v in report["speed_violations"]} == {
        "ascent_speed",
        "descent_speed",
    }


def test_airborne_minimum_not_hidden_by_ground_layout():
    report = validate_trajectories(
        {
            "A": [[0, 0, 0, 0], [1, 0, 0, 2], [2, 0, 0, 2]],
            "B": [[0, 0.5, 0, 0], [1, 4, 0, 2], [2, 0, 0, 2]],
        }
    )
    assert report["initial_layout"]["minimum_distance"] == 0.5
    air = report["separation_by_height"]["airborne_or_mixed"]
    assert air["minimum_distance"] == 0
    assert air["time"] == 2


def test_threshold_crossing_clips_pair_minimization():
    report = validate_trajectories(
        {
            "A": [[0, 0, 0, 0], [1, 0, 0, 1]],
            "B": [[0, 0, 0, 0], [1, 10, 0, 1]],
        },
        ground_clearance=0.5,
    )
    assert report["minimum_distance"] == 0
    air = report["separation_by_height"]["airborne_or_mixed"]
    assert air["minimum_distance"] == 5
    assert air["time"] == 0.5


def test_storyboard_boundary_splits_separation_checks():
    report = validate_trajectories(
        {
            "A": [[0, 0, 0, 0], [10, 0, 0, 0]],
            "B": [[0, 0, 0, 0], [10, 10, 0, 0]],
        },
        show_segments={"takeoff": (0, 2), "show": (2, 8), "landing": (8, 10)},
    )
    assert report["separation_by_storyboard_phase"]["show"]["minimum_distance"] == 2
    assert report["separation_by_storyboard_phase"]["landing"]["minimum_distance"] == 8


def test_overlap_is_unclassified_and_keeps_spacing_failure():
    report = validate_trajectories(
        {"A": [[0, 0, 0, 0]], "B": [[0, 0, 0, 0]]},
        show_segments={"takeoff": (0, 3), "show": (2, 4)},
    )
    assert report["storyboard_phases"]["status"] == "unavailable"
    assert report["storyboard_phases"]["issues"]
    assert "separation" in report["failed_checks"]


def test_acceleration_on_nonuniform_quadratic_samples():
    report = validate_trajectories(
        {"A": [[t, t * t, 0, 0] for t in (0, 0.5, 2, 3)]},
        max_acceleration=1,
        show_segments={"show": (0, 3)},
    )
    diagnostic = report["acceleration_estimates"]
    assert diagnostic["peaks"]["horizontal"]["value"] == pytest.approx(2)
    assert diagnostic["peaks"]["horizontal"]["phase"] == "show"
    assert diagnostic["status"] == "estimate_exceeds_limit"
    assert diagnostic["continuous_acceleration_verified"] is False
    assert report["diagnostic_warnings"] == ["acceleration_estimate_exceeds_limit"]


def test_short_paths_do_not_claim_acceleration_verification():
    report = validate_trajectories({"A": [[0, 0, 0, 0], [1, 1, 0, 0]]})
    assert report["acceleration_estimates"]["insufficient_samples"] == ["A"]
    assert report["acceleration_estimates"]["peaks"]["horizontal"] is None
    assert not report["acceleration_estimates"]["continuous_acceleration_verified"]


def test_500_drone_crossing_between_samples_is_detected():
    paths = {
        f"Drone {index}": [[0, index * 4, 0, 10], [10, index * 4, 0, 10]]
        for index in range(500)
    }
    paths["Drone 0"] = [[0, 0, 0, 10], [10, 4, 0, 10]]
    paths["Drone 1"] = [[0, 4, 0, 10], [10, 0, 0, 10]]
    report = validate_trajectories(paths)
    assert report["minimum_distance"] == 0
    assert report["closest_pair"]["time"] == 5
    assert "separation" in report["failed_checks"]


@pytest.mark.parametrize(
    "path",
    [
        [],
        [[0, 0, 0]],
        [[0, float("nan"), 0, 0]],
        [[1, 0, 0, 0], [1, 0, 0, 0]],
        [[-1, 0, 0, 0]],
    ],
)
def test_rejects_malformed_paths(path):
    with pytest.raises(ValueError):
        validate_trajectories({"A": path})
