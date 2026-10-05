"""Diagnostic estimates and authored phase labels; neither grants flight clearance."""

from math import isfinite

import numpy as np


def normalize_phases(segments):
    phases = []
    issues = []
    ambiguous = False
    for name, interval in (segments or {}).items():
        if name not in ("takeoff", "show", "landing"):
            issues.append(f"unknown phase: {name}")
            ambiguous = True
            continue
        try:
            valid = len(interval) == 2 and all(isfinite(v) for v in interval)
            valid = valid and interval[1] >= interval[0]
        except (TypeError, ValueError):
            valid = False
        if not valid:
            issues.append(f"invalid interval: {name}")
            ambiguous = True
            continue
        if interval[0] == interval[1]:
            issues.append(f"empty interval omitted: {name}")
            continue
        phases.append((float(interval[0]), float(interval[1]), name))
    phases.sort()
    if any(left[1] > right[0] for left, right in zip(phases, phases[1:])):
        issues.append("overlapping phase intervals")
        ambiguous = True
    # Ambiguous metadata never invents a phase or suppresses a check.
    return ([] if ambiguous else phases), issues


def phase_at(time, phases):
    return next(
        (name for start, end, name in phases if start <= time < end), "unclassified"
    )


def acceleration_diagnostics(names, paths, limit, phases):
    if not isfinite(limit) or limit < 0:
        raise ValueError("acceleration limit must be finite and nonnegative")
    peaks = {"horizontal": None, "vertical": None}
    violations = []
    insufficient = []
    for name, path in zip(names, paths):
        if len(path) < 3:
            insufficient.append(name)
            continue
        dt = np.diff(path[:, 0])
        velocity = np.diff(path[:, 1:], axis=0) / dt[:, None]
        acceleration = np.diff(velocity, axis=0) / ((dt[:-1] + dt[1:]) / 2)[:, None]
        for axis, values in (
            ("horizontal", np.linalg.norm(acceleration[:, :2], axis=1)),
            ("vertical", np.abs(acceleration[:, 2])),
        ):
            index = int(np.argmax(values))
            record = {
                "drone": name,
                "axis": axis,
                "value": float(values[index]),
                "time": float(path[index + 1, 0]),
                "window_start": float(path[index, 0]),
                "window_end": float(path[index + 2, 0]),
                "phase": phase_at(path[index + 1, 0], phases),
            }
            previous = peaks[axis]
            if previous is None or record["value"] > previous["value"]:
                peaks[axis] = record
            if record["value"] > limit + 1e-9:
                violations.append(record)
    return {
        "method": "difference of adjacent segment velocities divided by midpoint time separation",
        "limit_m_s2": limit,
        "status": "estimate_exceeds_limit" if violations else "no_estimated_exceedance",
        "continuous_acceleration_verified": False,
        "peaks": peaks,
        "violations": violations,
        "insufficient_samples": insufficient,
        "limitations": "finite-difference estimates on rounded, possibly simplified export samples; corners have velocity jumps; no bound on actual Blender acceleration",
    }
