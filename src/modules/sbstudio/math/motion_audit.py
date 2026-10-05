"""Sampled Blender-motion audit, distinct from continuous flight validation."""

from math import isfinite

import numpy as np

from .trajectory_validation import validate_trajectories


def audit_sampled_motion(
    paths, exported_paths, *, expected_sample_interval=None, **validation_options
):
    if paths.keys() != exported_paths.keys():
        raise ValueError("audit and export must contain the same drones")
    if expected_sample_interval is not None and (
        not isfinite(expected_sample_interval) or expected_sample_interval <= 0
    ):
        raise ValueError("audit sample interval must be finite and positive")
    report = validate_trajectories(paths, **validation_options)
    worst = {"distance_m": 0.0, "drone": None, "time": None}
    coverage_issues = []
    maximum_interval = 0.0
    for name, samples in paths.items():
        path = np.asarray(samples, dtype=float)
        exported = np.asarray(exported_paths[name], dtype=float)
        if (
            exported.ndim != 2
            or exported.shape[1] != 4
            or not len(exported)
            or not np.isfinite(exported).all()
            or (exported[:, 0] < 0).any()
            or (np.diff(exported[:, 0]) <= 0).any()
        ):
            raise ValueError(f"{name}: invalid exported path for motion audit")
        # Export timestamps are rounded to milliseconds. Allow only that
        # quantization error at the two endpoints, not an omitted audit range.
        if not np.allclose(
            path[[0, -1], 0], exported[[0, -1], 0], rtol=0, atol=0.000500001
        ):
            coverage_issues.append(f"{name}: audit/export time bounds differ")
        gaps = np.diff(path[:, 0])
        if len(gaps):
            maximum_interval = max(maximum_interval, float(gaps.max()))
        if expected_sample_interval is not None and (
            not len(gaps) or (gaps > expected_sample_interval + 1e-9).any()
        ):
            coverage_issues.append(f"{name}: missing dense audit samples")
        interpolated = np.column_stack(
            [
                np.interp(path[:, 0], exported[:, 0], exported[:, axis])
                for axis in (1, 2, 3)
            ]
        )
        distances = np.linalg.norm(path[:, 1:] - interpolated, axis=1)
        index = int(np.argmax(distances))
        if distances[index] > worst["distance_m"]:
            worst = {
                "distance_m": float(distances[index]),
                "drone": name,
                "time": float(path[index, 0]),
            }
    return {
        "scope": "evaluated position samples; linear interpolation between samples, not a continuous Blender-motion bound",
        "continuous_blender_motion_verified": False,
        "maximum_sampled_export_deviation": worst,
        "sample_count_per_drone": {name: len(path) for name, path in paths.items()},
        "sampling": {
            "expected_interval_seconds": expected_sample_interval,
            "maximum_interval_seconds": maximum_interval,
            "issues": coverage_issues,
        },
        "validation": report,
    }
