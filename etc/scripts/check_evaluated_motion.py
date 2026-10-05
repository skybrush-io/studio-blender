"""Blender background diagnostic: -- source.blend exported.skyc report.json.

Samples evaluated world positions every half-frame. This is a sampling audit,
not a continuous bound on arbitrary constraints, drivers or motion between samples.
Run with the built addon in an isolated Blender scripts directory.
"""

import json
import sys
from pathlib import Path
from time import perf_counter
from zipfile import ZipFile

import bpy
import numpy as np

bpy.ops.preferences.addon_enable(module="ui_skybrush_studio")

from sbstudio.math.trajectory_validation import validate_trajectories
from sbstudio.plugin.model.pyro_control import PyroControlPanelProperties
from sbstudio.plugin.model.safety_check import SafetyCheckProperties
from sbstudio.timing import effective_fps

PyroControlPanelProperties.ensure_overlays_enabled_if_needed = lambda self: None
SafetyCheckProperties.ensure_overlays_enabled_if_needed = lambda self: None
source, exported, output = sys.argv[sys.argv.index("--") + 1 :]
bpy.ops.wm.open_mainfile(filepath=source)
scene = bpy.context.scene
fps = effective_fps(scene.render)
with ZipFile(exported) as archive:
    show = json.loads(archive.read("show.json"))
    prior = json.loads(archive.read("validation.json"))
    exported_paths = {}
    for drone in show["swarm"]["drones"]:
        settings = drone["settings"]
        reference = settings["trajectory"]["$ref"].removeprefix("./").split("#")[0]
        points = json.loads(archive.read(reference))["points"]
        exported_paths[settings["name"]] = np.array([[t, *xyz] for t, xyz, _ in points])

# This harness audits full-scene exports only; fail instead of comparing misaligned clips.
assert abs((scene.frame_end - scene.frame_start) / fps - prior["time_range"][1]) < 0.002
frames = np.arange(scene.frame_start, scene.frame_end + 0.25, 0.5)
times = (frames - scene.frame_start) / fps
paths = {name: np.zeros((len(times), 4)) for name in exported_paths}
objects = {name: bpy.data.objects[name] for name in paths}
started = perf_counter()
for index, frame in enumerate(frames):
    scene.frame_set(int(frame), subframe=float(frame % 1))
    graph = bpy.context.evaluated_depsgraph_get()
    for name, obj in objects.items():
        paths[name][index] = [
            times[index],
            *obj.evaluated_get(graph).matrix_world.translation,
        ]
    if index % 4000 == 0:
        print(f"Evaluated {index}/{len(frames)} half-frames", flush=True)

worst = {"distance_m": 0.0}
for name, path in paths.items():
    exported_path = exported_paths[name]
    interpolated = np.column_stack(
        [
            np.interp(times, exported_path[:, 0], exported_path[:, axis])
            for axis in (1, 2, 3)
        ]
    )
    errors = np.linalg.norm(path[:, 1:] - interpolated, axis=1)
    index = int(np.argmax(errors))
    if errors[index] > worst["distance_m"]:
        worst = {
            "distance_m": float(errors[index]),
            "drone": name,
            "time": float(times[index]),
        }

report = validate_trajectories(
    paths,
    **prior["limits"],
    max_acceleration=prior["acceleration_estimates"]["limit_m_s2"],
    show_segments=show["meta"].get("segments"),
)
result = {
    "scope": "half-frame evaluated Blender world positions; linear interpolation only between samples",
    "continuous_blender_motion_verified": False,
    "sample_count_per_drone": len(times),
    "effective_fps": fps,
    "elapsed_seconds": perf_counter() - started,
    "maximum_sampled_export_deviation": worst,
    "validation": report,
}
Path(output).write_text(json.dumps(result, indent=2))
print(
    json.dumps(
        {key: value for key, value in result.items() if key != "validation"}, indent=2
    )
)
