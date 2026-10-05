"""Run in isolated background Blender: -- destination.skyc.

500 animated Blender objects, ten-minute full timeline, 4 Hz position samples,
compiled light programs, local backend validation and archive integrity checks.
This is a synthetic integration benchmark, not flight-system acceptance.
"""

import json
import sys
from pathlib import Path
from time import perf_counter
from zipfile import ZipFile

import bpy

try:
    import resource
except ImportError:  # Windows has no resource module; export testing still runs.
    resource = None

bpy.ops.preferences.addon_enable(module="ui_dronetara_studio")

from sbstudio.model.color import Color4D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.plugin.local_api import LocalSkybrushStudioAPI
from sbstudio.plugin.model.pyro_control import PyroControlPanelProperties
from sbstudio.plugin.model.safety_check import SafetyCheckProperties
from sbstudio.plugin.utils.motion_audit import sample_audit_positions
from sbstudio.plugin.utils.sampling import sample_positions_of_objects
from sbstudio.timing import effective_fps

PyroControlPanelProperties.ensure_overlays_enabled_if_needed = lambda self: None
SafetyCheckProperties.ensure_overlays_enabled_if_needed = lambda self: None

destination = Path(sys.argv[sys.argv.index("--") + 1])
scene = bpy.context.scene
scene.render.fps = 24
scene.render.fps_base = 1.001
objects = []
started = perf_counter()
for index in range(500):
    obj = bpy.data.objects.new(f"Stress {index:03}", None)
    scene.collection.objects.link(obj)
    x, y = (index % 25) * 4, (index // 25) * 4
    for frame, dx, height in [
        (0, 0, 0),
        (1440, 0, 30),
        (7200, 20, 40),
        (12960, 0, 30),
        (14400, 0, 0),
    ]:
        obj.location = (x + dx, y, height)
        obj.keyframe_insert(data_path="location", frame=frame)
    objects.append(obj)

paths = sample_positions_of_objects(objects, range(0, 14401, 6), context=bpy.context)
duration = 14400 / effective_fps(scene.render)
assert abs(duration - 600.6) < 0.001  # Blender stores fps_base as a float32.
lights = {}
for obj in objects:
    program = LightProgram()
    for time, rgb in [
        (0, (255, 0, 0)),
        (duration / 2, (0, 0, 255)),
        (duration, (0, 255, 0)),
    ]:
        program.append(Color4D(time, *rgb))
    lights[obj.name] = program
assert abs(paths[objects[0].name].points[-1].t - duration) < 1e-8
api = LocalSkybrushStudioAPI()
audit_enabled = "--audit" in sys.argv
evaluated = None
if audit_enabled:
    evaluated = sample_audit_positions(
        bpy.context,
        objects,
        (0, 14400),
        on_progress=lambda report: print(report.format(), flush=True) or False,
    )
api.export(
    trajectories=paths,
    lights=lights,
    output=destination,
    validation=SafetyCheckParams(),
    evaluated_motion=evaluated,
    evaluated_motion_sample_interval=1 / (2 * effective_fps(scene.render))
    if audit_enabled
    else None,
    export_policy="CHECKED" if audit_enabled else "PREVIEW",
    show_segments={
        "takeoff": (0, 60.06),
        "show": (60.06, 540.54),
        "landing": (540.54, duration),
    },
)
with ZipFile(destination) as archive:
    assert archive.testzip() is None
    report = json.loads(archive.read("validation.json"))
    assert report["drone_count"] == 500
    assert not report["failed_checks"], report["failed_checks"]
    assert not report["diagnostic_warnings"]
    if audit_enabled:
        assert report["export_gate"]["status"] == "passed_implemented_checks"
        assert report["export_gate"]["flight_approved"] is False
        assert report["evaluated_motion_audit"]["validation"]["drone_count"] == 500
        assert not report["evaluated_motion_audit"]["validation"]["failed_checks"]
    assert len(json.loads(archive.read("show.json"))["swarm"]["drones"]) == 500
result = {
    "export_gate_status": report["export_gate"]["status"],
    "maximum_sampled_export_deviation_m": report["evaluated_motion_audit"][
        "maximum_sampled_export_deviation"
    ]["distance_m"]
    if audit_enabled
    else None,
    "dense_audit_enabled": audit_enabled,
    "dense_samples_per_drone": 28801 if audit_enabled else None,
    "drone_count": 500,
    "samples_per_drone": 2401,
    "duration_seconds": duration,
    "elapsed_seconds": perf_counter() - started,
    "peak_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if resource is not None
    else None,
    "archive_bytes": destination.stat().st_size,
    "failed_checks": report["failed_checks"],
    "limitations": "single synthetic scene; no upload, cancellation, crash-recovery or flight acceptance test",
}
destination.with_suffix(".benchmark.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
