"""Offline export checks, deliberately separate from flight approval."""

from math import isfinite

CHECKED = "CHECKED"
PREVIEW = "PREVIEW"
DEFAULT_MAX_EXPORT_DEVIATION = 0.05


def validate_export_policy(policy, max_export_deviation):
    if policy not in (CHECKED, PREVIEW):
        raise ValueError("Unknown offline export policy")
    if not isfinite(max_export_deviation) or max_export_deviation <= 0:
        raise ValueError("Export deviation tolerance must be finite and positive")


def evaluate_export_gate(report, paths, *, policy, max_export_deviation):
    """Return a conservative review gate, never a flight-readiness verdict.

    A preview may retain failed checks for inspection. A checked draft requires
    both exported-path checks and a complete dense sampled audit. The deviation
    tolerance is an authoring-fidelity setting, not a vehicle tracking margin.
    """
    validate_export_policy(policy, max_export_deviation)
    reasons = list(report["failed_checks"]) + report.get("diagnostic_warnings", [])
    limits = report["limits"]
    if any(not isfinite(value) or value <= 0 for value in limits.values()):
        reasons.append("positive_safety_limits_required")
    if report["acceleration_estimates"]["limit_m_s2"] <= 0:
        reasons.append("positive_acceleration_limit_required")

    endpoints = {(path[0][0], path[-1][0]) for path in paths.values()}
    if len(endpoints) != 1 or any(
        start != 0 or end <= start for start, end in endpoints
    ):
        reasons.append("common_zero_based_positive_duration_required")
    phase_issues = report["storyboard_phases"]["issues"]
    if any(not issue.startswith("empty interval omitted:") for issue in phase_issues):
        reasons.append("invalid_phase_metadata")

    audit = report.get("evaluated_motion_audit")
    if audit is None:
        reasons.append("dense_motion_audit_required")
    else:
        reasons.extend(
            "evaluated_motion_" + check
            for check in audit["validation"]["failed_checks"]
        )
        reasons.extend(
            "evaluated_motion_" + check
            for check in audit["validation"]["diagnostic_warnings"]
        )
        if audit["sampling"]["issues"]:
            reasons.append("incomplete_dense_audit_coverage")
        if audit["sampling"]["expected_interval_seconds"] is None:
            reasons.append("dense_audit_sample_interval_required")
        if audit["validation"]["acceleration_estimates"]["insufficient_samples"]:
            reasons.append("insufficient_dense_acceleration_samples")
        deviation = audit["maximum_sampled_export_deviation"]["distance_m"]
        if not isfinite(deviation) or deviation > max_export_deviation + 1e-9:
            reasons.append("sampled_export_deviation_exceeds_tolerance")

    reasons = list(dict.fromkeys(reasons))
    return {
        "version": 1,
        "policy": policy,
        "status": "preview_only"
        if policy == PREVIEW
        else "blocked"
        if reasons
        else "passed_implemented_checks",
        "blocking_reasons": reasons,
        "maximum_export_deviation_m": max_export_deviation,
        "flight_approved": False,
        "requires_independent_flight_review": True,
        "limitations": list(report["not_evaluated"]),
    }


def offline_export_message(filepath, report):
    """Consistent UI messaging for foreground and worker-based exports."""
    gate = report.get("export_gate", {})
    warnings = report["failed_checks"] + report.get("diagnostic_warnings", [])
    if gate.get("status") == "passed_implemented_checks":
        return (
            {"INFO"},
            f"Checked draft saved to {filepath}; independent flight review still required",
        )
    message = f"PREVIEW ONLY saved to {filepath}; not approved for flight"
    if warnings:
        message += ". Warnings: " + ", ".join(dict.fromkeys(warnings))
    return {"WARNING"}, message
