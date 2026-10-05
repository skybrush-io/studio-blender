import pytest
from sbstudio.math.motion_audit import audit_sampled_motion


def test_dense_samples_expose_excursion_missing_from_export():
    exported = {"A": [[0, 0, 0, 0], [1, 0, 0, 0]]}
    actual = {"A": [[0, 0, 0, 0], [0.5, 0, 0, 5], [1, 0, 0, 0]]}
    report = audit_sampled_motion(actual, exported, max_velocity_z=2)
    assert report["maximum_sampled_export_deviation"]["distance_m"] == 5
    assert report["maximum_sampled_export_deviation"]["time"] == 0.5
    assert "ascent_speed" in report["validation"]["failed_checks"]
    assert not report["continuous_blender_motion_verified"]


def test_dense_samples_find_landing_convergence():
    paths = {
        "A": [[0, 0, 0, 10], [1, 0, 0, 0]],
        "B": [[0, 4, 0, 10], [1, 0, 0, 0]],
    }
    report = audit_sampled_motion(paths, paths, show_segments={"landing": (0, 1)})
    assert "separation" in report["validation"]["failed_checks"]
    assert (
        report["validation"]["separation_by_storyboard_phase"]["landing"][
            "minimum_distance"
        ]
        == 0
    )


def test_mismatched_drone_sets_rejected():
    with pytest.raises(ValueError, match="same drones"):
        audit_sampled_motion({"A": [[0, 0, 0, 0]]}, {})


@pytest.mark.parametrize("times", [[0.5, 0.75, 1], [0, 0.25, 0.5], [0, 0.25, 1]])
def test_missing_audit_range_or_samples_is_reported(times):
    exported = {"A": [[0, 0, 0, 0], [1, 0, 0, 0]]}
    actual = {"A": [[t, 0, 0, 0] for t in times]}
    report = audit_sampled_motion(actual, exported, expected_sample_interval=0.25)
    assert report["sampling"]["issues"]


def test_endpoint_timestamp_rounding_does_not_invalidate_complete_audit():
    exported = {"A": [[0, 0, 0, 0], [0.083, 0, 0, 0]]}
    actual = {"A": [[i / 48, 0, 0, 0] for i in range(5)]}
    report = audit_sampled_motion(actual, exported, expected_sample_interval=1 / 48)
    assert not report["sampling"]["issues"]


@pytest.mark.parametrize("interval", [0, -1, float("nan"), float("inf")])
def test_bad_audit_interval_rejected(interval):
    paths = {"A": [[0, 0, 0, 0], [1, 0, 0, 0]]}
    with pytest.raises(ValueError, match="interval"):
        audit_sampled_motion(paths, paths, expected_sample_interval=interval)


@pytest.mark.parametrize(
    "path", [[], [[0, 0, 0]], [[0, 0, 0, float("nan")]], [[1, 0, 0, 0], [0, 0, 0, 0]]]
)
def test_malformed_exported_path_is_not_silently_interpolated(path):
    actual = {"A": [[0, 0, 0, 0], [1, 0, 0, 0]]}
    with pytest.raises(ValueError, match="exported path"):
        audit_sampled_motion(actual, {"A": path})
