"""Isolated Blender acceptance: generic synthetic scenes, never user show files.

Run through run_isolated_blender_test.py --mode checked with a built add-on ZIP.
No uploads, vehicle commands or profile changes are performed.
"""

import json
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

import addon_utils
import bpy

assert addon_utils.enable("ui_skybrush_studio", default_set=True) is not None

import ui_skybrush_studio
from sbstudio.api.errors import SkybrushStudioAPIError
from sbstudio.background_job import BackgroundExportJob
from sbstudio.model.file_formats import FileFormat
from sbstudio.model.point import Point4D
from sbstudio.model.trajectory import Trajectory
from sbstudio.plugin import background_worker
from sbstudio.plugin.api import get_api
from sbstudio.plugin.errors import SkybrushStudioExportWarning
from sbstudio.plugin.local_api import LocalSkybrushStudioAPI
from sbstudio.plugin.model.global_settings import get_preferences
from sbstudio.plugin.operators.base import ExportOperator
from sbstudio.plugin.operators.export_to_skyc import _export_policy_updated
from sbstudio.plugin.operators.utils import export_show_to_file_using_api

root = Path(sys.argv[sys.argv.index("--") + 1])
root.mkdir(parents=True, exist_ok=True)
prefs = get_preferences()
prefs.operation_mode = "OFFLINE"
prefs.gateway_url = ""
network_attempts = []


def reject_network(*args, **kwargs):
    network_attempts.append("outbound Python socket attempted")
    raise RuntimeError("Network disabled in offline export acceptance test")


socket.socket.connect = reject_network
socket.create_connection = reject_network

scene = bpy.context.scene
scene.render.fps = 24
scene.render.fps_base = 1.001
collection = bpy.data.collections.new("Synthetic QA drones")
scene.collection.children.link(collection)
scene.skybrush.settings.drone_collection = collection
entry = scene.skybrush.storyboard.entries.add()
entry.name = "Synthetic QA interval"
entry.frame_start = 0
entry.duration = 121
entry.purpose = "SHOW"
objects = []
for index in range(100):
    obj = bpy.data.objects.new(f"QA {index:03}", None)
    collection.objects.link(obj)
    for frame, z in ((0, 10), (120, 11)):
        obj.location = ((index % 10) * 4, (index // 10) * 4, z)
        obj.keyframe_insert(data_path="location", frame=frame)
    objects.append(obj)

outcomes = {}


assert (
    bpy.ops.export_scene.skybrush.get_rna_type().properties["frame_range"].default
    == "RENDER"
)


def capture_export_range(operator, context):
    captured_ranges.append(operator.frame_range)
    return {"FINISHED"}


for mode, policy, explicit, expected in (
    ("COMMUNITY", "CHECKED", None, "RENDER"),
    ("COMMUNITY", "CHECKED", "STORYBOARD", "STORYBOARD"),
    ("OFFLINE", "CHECKED", None, "STORYBOARD"),
    ("OFFLINE", "CHECKED", "RENDER", "RENDER"),
    ("OFFLINE", "PREVIEW", None, "RENDER"),
    ("OFFLINE", "PREVIEW", "STORYBOARD", "STORYBOARD"),
):
    captured_ranges = []
    options = {"export_policy": policy}
    if explicit is not None:
        options["frame_range"] = explicit
    with (
        patch(
            "sbstudio.plugin.model.global_settings.get_preferences",
            return_value=SimpleNamespace(operation_mode=mode),
        ),
        patch.object(ExportOperator, "execute", capture_export_range),
    ):
        bpy.ops.export_scene.skybrush(**options)
    assert captured_ranges == [expected], (mode, policy, explicit, captured_ranges)
outcomes["frame_range_defaults"] = (
    "RNA defaults and six dispatch cases; server backend mocked"
)

for policy in ("CHECKED", "PREVIEW"):
    for option, label in (
        ("use_pyro_control", "Pyro"),
        ("export_audio", "Audio"),
        ("export_cameras", "Camera"),
    ):
        with patch(
            "sbstudio.plugin.operators.utils._get_frame_range_from_export_settings",
            side_effect=AssertionError("Preflight must precede sampling"),
        ):
            try:
                export_show_to_file_using_api(
                    LocalSkybrushStudioAPI(),
                    None,
                    {
                        "export_policy": policy,
                        "frame_range": "STORYBOARD",
                        option: True,
                    },
                    root / "unsupported.skyc",
                    FileFormat.SKYC,
                )
            except SkybrushStudioExportWarning as exc:
                assert label in str(exc), str(exc)
            else:
                raise AssertionError("Unsupported option was not rejected")
        outcomes[f"early_{policy}_{option}"] = (
            "rejected before sampling, including empty payload"
        )


def inspect_archive(destination, policy):
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        report = json.loads(archive.read("validation.json"))
        show = json.loads(archive.read("show.json"))
    assert report["drone_count"] == 100
    assert report["export_gate"]["policy"] == policy
    assert report["export_gate"]["flight_approved"] is False
    assert show["meta"]["skybrushExport"] == report["export_gate"]
    return report


def rejected(name, fragment, **settings):
    destination = root / f"{name}.skyc"
    destination.write_bytes(b"previous export must survive")
    try:
        result = bpy.ops.export_scene.skybrush(filepath=str(destination), **settings)
    except RuntimeError as exc:
        assert fragment in str(exc), str(exc)
    else:
        assert result == {"CANCELLED"}, result
    assert destination.read_bytes() == b"previous export must survive"
    assert get_api().last_validation_report is None
    outcomes[name] = "rejected; previous destination preserved"


destination = root / "checked 100 café.skyc"
assert bpy.ops.export_scene.skybrush(filepath=str(destination)) == {"FINISHED"}
report = inspect_archive(destination, "CHECKED")
assert report["export_gate"]["status"] == "passed_implemented_checks"
assert report["evaluated_motion_audit"]["sample_count_per_drone"]["QA 000"] == 241
outcomes["default_checked_export"] = (
    "100 drones; dense audit forced; fractional FPS; Unicode filename"
)
properties = bpy.context.window_manager.operator_properties_last(
    "export_scene.skybrush"
)
properties.export_policy = "PREVIEW"
properties.export_selected = True
properties.frame_range = "RENDER"
properties.export_policy = "CHECKED"
_export_policy_updated(
    properties, SimpleNamespace(space_data=SimpleNamespace(type="FILE_BROWSER"))
)
assert properties.export_selected is False and properties.frame_range == "STORYBOARD"
outcomes["checked_policy_reset"] = (
    "simulated file-browser policy switch resets all-drones/full-storyboard controls"
)

assert bpy.ops.wm.save_as_mainfile(
    filepath=str(root / "synthetic-100.blend"), copy=True, relative_remap=True
) == {"FINISHED"}

# Preflight rejections must clear stale validation state as well as protect files.
rejected("selected_clip", "all drones", export_selected=True)
rejected("render_clip", "Storyboard", frame_range="RENDER")
rejected("yaw_unvalidated", "yaw", use_yaw_control=True)


def worker_export(name, should_pass):
    destination = root / f"{name}.skyc"
    destination.write_bytes(b"previous worker output")
    job = BackgroundExportJob(destination)
    original = bpy.data.filepath, scene.frame_current
    try:
        snapshot = job.directory / "snapshot.blend"
        assert bpy.ops.wm.save_as_mainfile(
            filepath=str(snapshot), copy=True, relative_remap=True
        ) == {"FINISHED"}
        config = {
            "addon_directory": str(Path(ui_skybrush_studio.__file__).parent),
            "addon_module": "ui_skybrush_studio",
            "snapshot": str(snapshot),
            "artifact": str(job.artifact),
            "format": "skyc",
            "scene": scene.name,
            "view_layer": bpy.context.view_layer.name,
            "settings": {
                "frame_range": "STORYBOARD",
                "output_fps": 4,
                "light_output_fps": 4,
                "redraw": False,
            },
        }
        config_path = job.directory / "config.json"
        config_path.write_text(json.dumps(config))
        job.start(
            [
                bpy.app.binary_path,
                "--background",
                "--factory-startup",
                "--disable-autoexec",
                "--python-exit-code",
                "1",
                "--python",
                str(background_worker.__file__),
                "--",
                str(config_path),
            ]
        )
        code = job.process.wait(timeout=180)
        if should_pass:
            assert code == 0, job.error_message()
            assert not job.commit()
            assert job.export_gate["status"] == "passed_implemented_checks"
            inspect_archive(destination, "CHECKED")
        else:
            assert code != 0
            assert "separation" in job.error_message()
            assert not job.artifact.exists()
            assert destination.read_bytes() == b"previous worker output"
        assert original == (bpy.data.filepath, scene.frame_current)
        outcomes[name] = (
            "passed" if should_pass else "rejected; previous destination preserved"
        )
    finally:
        job.close()


worker_export("checked_worker", True)

# Duplicate one full path, not just an endpoint. The gate must reject the show.
objects[1].animation_data_clear()
constraint = objects[1].constraints.new("COPY_LOCATION")
constraint.target = objects[0]
scene.frame_set(0)
bpy.context.view_layer.update()
assert (
    objects[1].matrix_world.translation - objects[0].matrix_world.translation
).length < 1e-6
rejected("colliding_show", "separation")
worker_export("colliding_worker", False)
preview = root / "preview only.skyc"
assert bpy.ops.export_scene.skybrush(
    filepath=str(preview), export_policy="PREVIEW"
) == {"FINISHED"}
preview_report = inspect_archive(preview, "PREVIEW")
assert "separation" in preview_report["failed_checks"]
assert preview_report["export_gate"]["status"] == "preview_only"
outcomes["explicit_preview"] = "saved known violations with preview-only metadata"


def direct_rejection(name, paths, evaluated, fragment, **options):
    destination = root / f"{name}.skyc"
    destination.write_bytes(b"previous direct output")
    api = LocalSkybrushStudioAPI()
    try:
        api.export(
            trajectories={
                key: Trajectory([Point4D(*point) for point in path])
                for key, path in paths.items()
            },
            evaluated_motion=evaluated,
            evaluated_motion_sample_interval=0.5,
            output=destination,
            **options,
        )
    except (SkybrushStudioAPIError, ValueError) as exc:
        assert fragment in str(exc), str(exc)
    else:
        raise AssertionError(f"{name} was not rejected")
    assert destination.read_bytes() == b"previous direct output"
    assert api.last_validation_report is None
    outcomes[name] = "rejected; previous destination preserved"


crossing = {
    "A": [[0, -2, 0, 10], [0.5, 2, 0, 10], [1, 6, 0, 10]],
    "B": [[0, 2, 0, 10], [0.5, -2, 0, 10], [1, -6, 0, 10]],
}
direct_rejection("between_samples_collision", crossing, crossing, "separation")
overspeed = {"A": [[0, 0, 0, 0], [0.5, 0, 0, 2], [1, 0, 0, 4]]}
direct_rejection("vertical_overspeed", overspeed, overspeed, "ascent_speed")
stationary = {"A": [[0, 0, 0, 10], [0.5, 0, 0, 10], [1, 0, 0, 10]]}
drift = {"A": [[0, 0.1, 0, 10], [0.5, 0.1, 0, 10], [1, 0.1, 0, 10]]}
direct_rejection(
    "excessive_export_deviation", stationary, drift, "sampled_export_deviation"
)
direct_rejection("missing_audit", stationary, None, "dense motion audit")
direct_rejection(
    "missing_audit_range", stationary, {"A": stationary["A"][1:]}, "coverage"
)
direct_rejection(
    "invalid_tolerance",
    stationary,
    stationary,
    "tolerance",
    max_export_deviation=float("nan"),
)

assert not network_attempts, network_attempts
result = {
    "addon_version": list(ui_skybrush_studio.bl_info["version"]),
    "blender_version": bpy.app.version_string,
    "cases": outcomes,
    "python_network_attempts_in_parent": network_attempts,
    "scope": "synthetic offline export acceptance; not hardware/flight acceptance or live GUI testing",
}
(root / "checked-export-results.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
