"""Isolated Blender regression checks for audit cancellation and scene restoration."""

from pathlib import Path
from tempfile import TemporaryDirectory

import bpy
import numpy as np

bpy.ops.preferences.addon_enable(module="ui_skybrush_studio")

from sbstudio.plugin.errors import TaskCancelled
from sbstudio.plugin.model.pyro_control import PyroControlPanelProperties
from sbstudio.plugin.model.safety_check import SafetyCheckProperties
from sbstudio.plugin.utils.motion_audit import sample_audit_positions

PyroControlPanelProperties.ensure_overlays_enabled_if_needed = lambda self: None
SafetyCheckProperties.ensure_overlays_enabled_if_needed = lambda self: None
scene = bpy.context.scene
obj = bpy.data.objects.new("Audit regression", None)
scene.collection.objects.link(obj)
obj.driver_add("location", 0).driver.expression = "frame"
scene.frame_set(7, subframe=0.25)
try:
    sample_audit_positions(bpy.context, [obj], (0, 100), on_progress=lambda _: True)
except TaskCancelled:
    pass
else:
    raise AssertionError("cancellation did not propagate")
assert scene.frame_current == 7 and scene.frame_subframe == 0.25
paths = sample_audit_positions(bpy.context, [obj], (-1, 1))
assert len(paths[obj.name]) == 5
np.testing.assert_allclose(paths[obj.name][:, 1], [-1, -0.5, 0, 0.5, 1], atol=1e-6)
assert scene.frame_current == 7 and scene.frame_subframe == 0.25


class BrokenObject:
    name = "Broken"

    def evaluated_get(self, graph):
        raise RuntimeError("simulated evaluation failure")


try:
    sample_audit_positions(bpy.context, [BrokenObject()], (0, 10))
except RuntimeError as exc:
    assert "simulated" in str(exc)
else:
    raise AssertionError("evaluation failure swallowed")
assert scene.frame_current == 7 and scene.frame_subframe == 0.25
print("Audit cancellation, negative frames and restoration regressions passed")

from sbstudio.model.point import Point4D
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin.local_api import LocalSkybrushStudioAPI
from sbstudio.plugin.utils.validation_progress import validation_progress_callback

trajectory = Trajectory()
for time in (0, 1, 2):
    trajectory.append(Point4D(time, 0, 0, time))
with TemporaryDirectory(prefix="skybrush-cancellation-") as directory:
    destination = Path(directory) / "existing.skyc"
    for stage in (
        "Exported path validation",
        "Dense motion validation",
        "Ready to save export",
    ):
        destination.write_bytes(b"previous export")
        api = LocalSkybrushStudioAPI()
        callback = validation_progress_callback(
            lambda report, stage=stage: report.operation == stage
        )
        try:
            api.export(
                trajectories={"A": trajectory},
                output=destination,
                evaluated_motion={"A": [[0, 0, 0, 0], [1, 0, 0, 1], [2, 0, 0, 2]]},
                evaluated_motion_sample_interval=1,
                validation_progress=callback,
            )
        except TaskCancelled:
            pass
        else:
            raise AssertionError(f"Cancellation failed at {stage}")
        assert destination.read_bytes() == b"previous export"
        assert api.last_validation_report is None
        assert list(Path(directory).iterdir()) == [destination]
print("Exported/dense validation and pre-save cancellation preserved prior export")
