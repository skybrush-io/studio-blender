from copy import deepcopy

import pytest
from sbstudio.export_policy import evaluate_export_gate, offline_export_message
from sbstudio.math.motion_audit import audit_sampled_motion
from sbstudio.math.trajectory_validation import validate_trajectories


def evidence():
    paths = {
        "A": [[0, 0, 0, 0], [0.5, 0, 0, 0.5], [1, 0, 0, 1]],
        "B": [[0, 4, 0, 0], [0.5, 4, 0, 0.5], [1, 4, 0, 1]],
    }
    report = validate_trajectories(paths, show_segments={"show": (0, 1)})
    report["evaluated_motion_audit"] = audit_sampled_motion(
        paths,
        paths,
        expected_sample_interval=0.5,
    )
    return paths, report


def gate(paths, report, policy="CHECKED", tolerance=0.05):
    return evaluate_export_gate(
        report, paths, policy=policy, max_export_deviation=tolerance
    )


def test_passing_checks_never_grant_flight_approval():
    paths, report = evidence()
    result = gate(paths, report)
    assert result["status"] == "passed_implemented_checks"
    assert not result["blocking_reasons"]
    assert result["flight_approved"] is False
    assert result["requires_independent_flight_review"] is True
    assert "vehicle tracking error" in result["limitations"]


@pytest.mark.parametrize(
    "check",
    ["separation", "altitude", "horizontal_speed", "ascent_speed", "descent_speed"],
)
def test_each_known_failure_blocks(check):
    paths, report = evidence()
    report["failed_checks"] = [check]
    assert check in gate(paths, report)["blocking_reasons"]


@pytest.mark.parametrize(
    "change,reason",
    [
        ("no_audit", "dense_motion_audit_required"),
        ("audit_failure", "evaluated_motion_separation"),
        ("audit_acceleration", "evaluated_motion_acceleration_estimate_exceeds_limit"),
        ("short_audit", "incomplete_dense_audit_coverage"),
        ("unknown_interval", "dense_audit_sample_interval_required"),
        ("insufficient_samples", "insufficient_dense_acceleration_samples"),
        ("deviation", "sampled_export_deviation_exceeds_tolerance"),
        ("zero_limit", "positive_safety_limits_required"),
        ("zero_acceleration", "positive_acceleration_limit_required"),
        ("bad_phases", "invalid_phase_metadata"),
    ],
)
def test_missing_or_failed_evidence_blocks(change, reason):
    paths, report = evidence()
    audit = report["evaluated_motion_audit"]
    if change == "no_audit":
        del report["evaluated_motion_audit"]
    elif change == "audit_failure":
        audit["validation"]["failed_checks"] = ["separation"]
    elif change == "audit_acceleration":
        audit["validation"]["diagnostic_warnings"] = [
            "acceleration_estimate_exceeds_limit"
        ]
    elif change == "short_audit":
        audit["sampling"]["issues"] = ["A: missing samples"]
    elif change == "unknown_interval":
        audit["sampling"]["expected_interval_seconds"] = None
    elif change == "insufficient_samples":
        audit["validation"]["acceleration_estimates"]["insufficient_samples"] = ["A"]
    elif change == "deviation":
        audit["maximum_sampled_export_deviation"]["distance_m"] = 0.051
    elif change == "zero_limit":
        report["limits"]["min_distance"] = 0
    elif change == "zero_acceleration":
        report["acceleration_estimates"]["limit_m_s2"] = 0
    elif change == "bad_phases":
        report["storyboard_phases"]["issues"] = ["overlapping phase intervals"]
    result = gate(paths, report)
    assert result["status"] == "blocked"
    assert reason in result["blocking_reasons"]


def test_preview_is_never_reported_as_checked_even_when_checks_pass():
    paths, report = evidence()
    assert gate(paths, report, "PREVIEW")["status"] == "preview_only"
    report["failed_checks"] = ["separation"]
    assert gate(paths, report, "PREVIEW")["blocking_reasons"] == ["separation"]


@pytest.mark.parametrize("start,end", [(0.1, 1), (0, 0.5), (0, 0)])
def test_mismatched_or_empty_timing_blocks(start, end):
    paths, report = evidence()
    paths["A"][0][0], paths["A"][-1][0] = start, end
    assert (
        "common_zero_based_positive_duration_required"
        in gate(paths, report)["blocking_reasons"]
    )


@pytest.mark.parametrize("tolerance", [0, -1, float("nan"), float("inf")])
def test_invalid_tolerance_rejected(tolerance):
    paths, report = evidence()
    with pytest.raises(ValueError, match="tolerance"):
        gate(paths, report, tolerance=tolerance)


def test_unknown_policy_rejected():
    paths, report = evidence()
    with pytest.raises(ValueError, match="policy"):
        gate(paths, report, "FORCE")


def test_policy_does_not_mutate_report():
    paths, report = evidence()
    original = deepcopy(report)
    gate(paths, report)
    assert report == original


@pytest.mark.parametrize(
    "policy,level,phrase",
    [
        ("CHECKED", {"INFO"}, "independent flight review"),
        ("PREVIEW", {"WARNING"}, "PREVIEW ONLY"),
    ],
)
def test_completion_message_has_explicit_scope(policy, level, phrase):
    paths, report = evidence()
    report["export_gate"] = gate(paths, report, policy)
    actual_level, message = offline_export_message("example.skyc", report)
    assert actual_level == level
    assert phrase in message
    assert "example.skyc" in message
    assert "Export successful" not in message
