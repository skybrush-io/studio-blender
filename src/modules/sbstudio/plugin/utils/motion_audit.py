"""Evaluate dense world-space motion without changing the exported trajectories."""

from math import floor

import numpy as np

from sbstudio.timing import effective_fps

from .progress import StepBasedProgressReport, report_progress


def sample_audit_positions(context, drones, bounds, on_progress=None):
    scene = context.scene
    count = 2 * (bounds[1] - bounds[0]) + 1
    if count * len(drones) > 20_000_000:
        raise ValueError(
            "Dense motion audit exceeds 20 million samples; export a shorter range"
        )
    paths = {obj.name: np.empty((count, 4)) for obj in drones}
    original = scene.frame_current, scene.frame_subframe
    fps = effective_fps(scene.render)
    try:
        for index in report_progress(
            range(count),
            operation="Auditing evaluated motion at half-frame intervals",
            on_progress=on_progress,
            report_factory=StepBasedProgressReport,
        ):
            frame = bounds[0] + index / 2
            scene.frame_set(floor(frame), subframe=frame % 1)
            graph = context.evaluated_depsgraph_get()
            for obj in drones:
                paths[obj.name][index] = [
                    index / (2 * fps),
                    *obj.evaluated_get(graph).matrix_world.translation,
                ]
    finally:
        scene.frame_set(original[0], subframe=original[1])
    return paths
