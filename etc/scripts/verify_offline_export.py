"""Run inside isolated Blender with the built add-on installed.

Usage: blender --background --factory-startup --disable-autoexec
  --python-exit-code 1 --python this_file -- source.blend destination.skyc
"""

import json
import sys
from pathlib import Path
from zipfile import ZipFile

import bpy

bpy.ops.preferences.addon_enable(module="ui_dronetara_studio")

from sbstudio.plugin.model.pyro_control import PyroControlPanelProperties
from sbstudio.plugin.model.safety_check import SafetyCheckProperties

# The background process has no graphics context for viewport overlays.
PyroControlPanelProperties.ensure_overlays_enabled_if_needed = lambda self: None
SafetyCheckProperties.ensure_overlays_enabled_if_needed = lambda self: None

arguments = sys.argv[sys.argv.index("--") + 1 :]
audit = "--audit" in arguments
source, destination = [arg for arg in arguments if arg != "--audit"]
bpy.ops.wm.open_mainfile(filepath=source)
bpy.context.preferences.addons[
    "ui_dronetara_studio"
].preferences.operation_mode = "OFFLINE"
result = bpy.ops.export_scene.skybrush(
    filepath=destination, audit_motion=audit, export_policy="PREVIEW"
)
assert result == {"FINISHED"}, result
with ZipFile(destination) as archive:
    assert archive.testzip() is None
    report = json.loads(archive.read("validation.json"))
    show = json.loads(archive.read("show.json"))
    assert report["drone_count"] == len(show["swarm"]["drones"])
    if audit:
        assert "evaluated_motion_audit" in report
        assert not report["evaluated_motion_audit"][
            "continuous_blender_motion_verified"
        ]
Path(destination).with_suffix(".validation.json").write_text(
    json.dumps(report, indent=2)
)
print(
    json.dumps(
        {
            "output": destination,
            "size": Path(destination).stat().st_size,
            "validation": report,
        },
        indent=2,
    )
)
