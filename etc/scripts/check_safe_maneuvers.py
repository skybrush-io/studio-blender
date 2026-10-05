"""Packaged Blender acceptance for 5.10.0 offline landing and Smart RTH.

Run with run_isolated_blender_test.py --mode maneuvers. Synthetic scenes only;
the runner uses an isolated profile. No uploads, normal-profile installs or GUI
acceptance claims. The same script is used on macOS and Windows.
"""

import json
import platform
import socket
import sys
from pathlib import Path
from time import perf_counter
from zipfile import ZipFile

import addon_utils
import bpy
import numpy as np

assert addon_utils.enable("ui_dronetara_studio", default_set=True) is not None

import ui_dronetara_studio
from sbstudio.math.safe_maneuvers import ManeuverLimits, plan_checked_landing
from sbstudio.plugin.actions import iter_all_f_curves
from sbstudio.plugin.model.global_settings import get_preferences
from sbstudio.plugin.model.pyro_control import PyroControlPanelProperties
from sbstudio.plugin.model.safety_check import SafetyCheckProperties
from sbstudio.plugin.utils import safe_maneuvers
from sbstudio.timing import effective_fps

assert ui_dronetara_studio.bl_info["version"] == (5, 10, 0)
get_preferences().operation_mode = "OFFLINE"
get_preferences().gateway_url = ""
PyroControlPanelProperties.ensure_overlays_enabled_if_needed = lambda self: None
SafetyCheckProperties.ensure_overlays_enabled_if_needed = lambda self: None
outcomes, network_attempts = {}, []
root = Path(sys.argv[sys.argv.index("--") + 1])
root.mkdir(parents=True, exist_ok=True)


def reject_network(*args, **kwargs):
    network_attempts.append(True)
    raise RuntimeError("Network disabled for maneuver acceptance")


socket.socket.connect = socket.create_connection = reject_network
scene = bpy.context.scene
storyboard = scene.skybrush.storyboard


def fixture(source, home=None):
    # Everything here belongs to this isolated synthetic test session.
    storyboard.entries.clear()
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for action in list(bpy.data.actions):
        if action.users == 0:
            bpy.data.actions.remove(action)
    scene.render.fps = 24
    scene.render.fps_base = 1.001
    collection = bpy.data.collections.new("Synthetic QA fleet")
    scene.collection.children.link(collection)
    scene.skybrush.settings.drone_collection = collection
    scene.skybrush.safety_check.proximity_warning_threshold = 3
    scene.skybrush.safety_check.altitude_warning_threshold = 150
    scene.skybrush.safety_check.velocity_xy_warning_threshold = 10
    scene.skybrush.safety_check.velocity_z_warning_threshold = 2
    scene.skybrush.safety_check.acceleration_warning_threshold = 4
    scene.skybrush.settings.max_acceleration = 4
    entry = storyboard.entries.add()
    entry.name = "Synthetic preceding show"
    entry.frame_start, entry.duration, entry.purpose = 0, 481, "SHOW"
    drones = []
    for i, point in enumerate(source):
        drone = bpy.data.objects.new(f"QA {i:03}", None)
        collection.objects.link(drone)
        for frame, location in (
            (0, home[i] if home is not None else point),
            (480, point),
        ):
            drone.location = location
            drone.keyframe_insert(data_path="location", frame=frame)
        drones.append(drone)
    scene.frame_set(480, subframe=0.25)
    return drones


def snapshot(drones):
    return {
        "entries": [
            (e.name, e.frame_start, e.duration, e.mapping) for e in storyboard.entries
        ],
        "objects": sorted(bpy.data.objects.keys()),
        "collections": sorted(bpy.data.collections.keys()),
        "actions": sorted(bpy.data.actions.keys()),
        "constraints": [[c.name for c in d.constraints] for d in drones],
        "curves": [
            [
                (c.data_path, c.array_index, [tuple(k.co) for k in c.keyframe_points])
                for c in iter_all_f_curves(d.animation_data)
            ]
            for d in drones
        ],
        "frame": (scene.frame_current, scene.frame_subframe),
    }


def rejected(name, operation, drones, text):
    before = snapshot(drones)
    try:
        result = operation()
    except RuntimeError as exc:
        assert text in str(exc), str(exc)
    else:
        assert result == {"CANCELLED"}, result
    assert snapshot(drones) == before, name
    outcomes[name] = "rejected without changing scene animation"


def verify_installed(drones, expected_final):
    entry = storyboard.last_entry
    assert entry.is_locked and entry.transition_type == "MANUAL"
    assert entry.get_mapping() == list(range(len(drones)))
    report = json.loads(entry.formation["dronetara_maneuver"])
    assert not report["flight_approved"]
    frames = report["frames"]
    markers = [drone.constraints[-1].target for drone in drones]
    for marker in markers:
        curves = list(iter_all_f_curves(marker.animation_data))
        assert len(curves) == 3
        for curve in curves:
            assert not curve.modifiers and curve.extrapolation == "CONSTANT"
            for key in curve.keyframe_points:
                assert key.interpolation == "BEZIER"
                assert key.handle_left_type == key.handle_right_type == "FREE"
    for begin, end in zip(frames, frames[1:]):
        for frame in np.linspace(begin, end, 21):
            scene.frame_set(int(frame), subframe=float(frame % 1))
            points = np.asarray([tuple(d.matrix_world.translation) for d in drones])
            expected = np.asarray([tuple(m.matrix_world.translation) for m in markers])
            np.testing.assert_allclose(points, expected, rtol=0, atol=1e-4)
            distances = np.linalg.norm(points[:, None] - points[None, :], axis=2)
            np.fill_diagonal(distances, np.inf)
            assert distances.min() >= 3 - 1e-4
    scene.frame_set(frames[-1] + 3)
    np.testing.assert_allclose(
        [tuple(d.matrix_world.translation) for d in drones],
        expected_final,
        rtol=0,
        atol=1e-4,
    )
    # Recalculating an ordinary transition must not reassign the checked route.
    before = snapshot(drones)
    bpy.ops.skybrush.recalculate_transitions(scope="ALL")
    assert snapshot(drones) == before
    return report


drones = fixture([(0, 0, 10), (4, 0, 4), (8, 0, 0)])
assert bpy.ops.skybrush.land(start_frame=480, velocity=1, altitude=0) == {"FINISHED"}
report = verify_installed(drones, [(0, 0, 0), (4, 0, 0), (8, 0, 0)])
assert report["duration_seconds"] >= 15
outcomes["smooth_landing_fractional_fps_stationary_drone"] = report

drones = fixture([(0, 0, 10), (0.5, 0, 15)])
rejected(
    "close_landing",
    lambda: bpy.ops.skybrush.land(start_frame=480),
    drones,
    "Landing layout",
)
drones = fixture([(0, 0, 10), (4, 0, 10)])
rejected(
    "wrong_start_frame",
    lambda: bpy.ops.skybrush.land(start_frame=500),
    drones,
    "last storyboard frame",
)
rejected(
    "upward_landing",
    lambda: bpy.ops.skybrush.land(start_frame=480, altitude=11),
    drones,
    "above",
)

home = [(10, 0, 2), (0, 0, 5)]
drones = fixture([(0, 0, 10), (10, 0, 10)], home)
assert bpy.ops.skybrush.rth(start_frame=480, use_smart_rth=False, altitude=20) == {
    "FINISHED"
}
report = verify_installed(drones, home)
assert report["layers"] == 2
outcomes["crossing_rth_home_z_identity_legacy_toggle"] = report
assert bpy.ops.wm.save_as_mainfile(
    filepath=str(root / "checked RTH café.blend"), copy=True
) == {"FINISHED"}
assert bpy.ops.wm.open_mainfile(filepath=str(root / "checked RTH café.blend")) == {
    "FINISHED"
}
scene = bpy.context.scene
storyboard = scene.skybrush.storyboard
drones = list(scene.skybrush.settings.drone_collection.objects)
verify_installed(drones, home)
outcomes["save_reopen_preserves_paths"] = True

drones = fixture([(0, 0, 10), (10, 0, 10)], home)
assert bpy.ops.skybrush.rth(start_frame=480, to_aerial_grid=True, altitude=15) == {
    "FINISHED"
}
verify_installed(drones, [(10, 0, 15), (0, 0, 15)])
outcomes["aerial_grid_no_unchecked_descent"] = True

drones = fixture([(0, 0, 10), (10, 0, 10)], [(0, 0, 0), (0.5, 0, 0)])
rejected(
    "close_home", lambda: bpy.ops.skybrush.rth(start_frame=480), drones, "Home layout"
)
drones = fixture([(0, 0, 10), (10, 0, 10)], home)
scene.skybrush.safety_check.altitude_warning_threshold = 22
rejected(
    "ceiling_capacity",
    lambda: bpy.ops.skybrush.rth(start_frame=480, altitude=20),
    drones,
    "altitude ceiling",
)

drones = fixture([(0, 0, 10), (4, 0, 10)])
plan = plan_checked_landing(
    [(0, 0, 10), (4, 0, 10)],
    target_altitude=0,
    limits=ManeuverLimits(3, 150, 4, 1, 4),
    fps=effective_fps(scene.render),
    start_frame=481,
)
# Fail midway through adding drone constraints; all prior user animation survives.
original = safe_maneuvers.ensure_f_curve_exists_for_data_path_and_index


def fail_second_constraint(obj, **kwargs):
    if obj == drones[1]:
        raise RuntimeError("Injected constraint installation failure")
    return original(obj, **kwargs)


before = snapshot(drones)
safe_maneuvers.ensure_f_curve_exists_for_data_path_and_index = fail_second_constraint
try:
    try:
        safe_maneuvers.install_maneuver(
            plan, drones, storyboard, name="Failure injection", context=bpy.context
        )
    except RuntimeError as exc:
        assert "Injected" in str(exc)
    else:
        raise AssertionError("Expected installation failure")
finally:
    safe_maneuvers.ensure_f_curve_exists_for_data_path_and_index = original
assert snapshot(drones) == before, {
    key: (before[key], value)
    for key, value in snapshot(drones).items()
    if before[key] != value
}
outcomes["partial_installation_rollback"] = True

drones = fixture([(0, 0, 10), (4, 0, 10)])
drones[0].driver_add("location", 0).driver.expression = "0"
rejected(
    "unsupported_driver",
    lambda: bpy.ops.skybrush.land(start_frame=480),
    drones,
    "drivers",
)

for count in (100, 500):
    home = np.array([(i % 20 * 4, i // 20 * 4, 0) for i in range(count)], dtype=float)
    swapped = home[np.arange(count).reshape(-1, 2)[:, ::-1].ravel()] + [0, 0, 10]
    drones = fixture(swapped, home)
    started = perf_counter()
    assert bpy.ops.skybrush.rth(start_frame=480, altitude=20) == {"FINISHED"}
    report = verify_installed(drones, home)
    outcomes[f"{count}_drone_crossing_rth"] = dict(
        report, test_elapsed_seconds=perf_counter() - started
    )
    drones = fixture(home + [0, 0, 10])
    started = perf_counter()
    assert bpy.ops.skybrush.land(start_frame=480) == {"FINISHED"}
    report = verify_installed(drones, home)
    outcomes[f"{count}_drone_landing"] = dict(
        report, test_elapsed_seconds=perf_counter() - started
    )

# A complete safe synthetic show, unlike the deliberately crossing preceding
# fixtures above, must also pass the existing checked export gate.
home = np.array([(i % 10 * 4, i // 10 * 4, 0) for i in range(100)], dtype=float)
drones = fixture(home + [20, 0, 10], home)
assert bpy.ops.skybrush.rth(start_frame=480, altitude=20) == {"FINISHED"}
verify_installed(drones, home)
destination = root / "100 checked RTH café.skyc"
assert bpy.ops.export_scene.skybrush(filepath=str(destination)) == {"FINISHED"}
with ZipFile(destination) as archive:
    assert archive.testzip() is None
    validation = json.loads(archive.read("validation.json"))
assert validation["export_gate"]["status"] == "passed_implemented_checks"
assert not validation["failed_checks"]
assert not validation["export_gate"]["flight_approved"]
outcomes["complete_show_checked_export"] = "100 drones; archive and dense audit passed"
assert not network_attempts
result = {
    "platform": platform.platform(),
    "blender": bpy.app.version_string,
    "version": ui_dronetara_studio.bl_info["version"],
    "outcomes": outcomes,
    "network_attempts": len(network_attempts),
    "flight_approved": False,
}
(root / "maneuver-results.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8"
)
print(json.dumps(result, indent=2), flush=True)
