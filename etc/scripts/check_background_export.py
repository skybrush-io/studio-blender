"""Blender integration: -- source.blend destination.skyc; tests worker + snapshot."""

import json
import sys
from pathlib import Path
from zipfile import ZipFile

import bpy

bpy.ops.preferences.addon_enable(module="ui_skybrush_studio")

import ui_skybrush_studio
from sbstudio.background_job import BackgroundExportJob
from sbstudio.plugin import background_worker

source, output = sys.argv[sys.argv.index("--") + 1 :]
bpy.ops.wm.open_mainfile(filepath=source, use_scripts=False)
original = bpy.data.filepath, bpy.context.scene.frame_current
job = BackgroundExportJob(output)
try:
    snapshot = job.directory / "snapshot.blend"
    assert bpy.ops.wm.save_as_mainfile(
        filepath=str(snapshot), copy=True, relative_remap=True
    ) == {"FINISHED"}
    assert (bpy.data.filepath, bpy.context.scene.frame_current) == original
    config = {
        "addon_directory": str(Path(ui_skybrush_studio.__file__).parent),
        "addon_module": "ui_skybrush_studio",
        "snapshot": str(snapshot),
        "artifact": str(job.artifact),
        "format": "skyc",
        "scene": bpy.context.scene.name,
        "view_layer": bpy.context.view_layer.name,
        "settings": {
            "export_policy": "PREVIEW",  # This regression intentionally retains warnings.
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
            background_worker.__file__,
            "--",
            str(config_path),
        ]
    )
    code = job.process.wait(timeout=180)
    if code:
        raise AssertionError(
            job.error_message() + "\n" + (job.directory / "worker.log").read_text()
        )
    warnings = job.commit()
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        report = json.loads(archive.read("validation.json"))
        assert report["drone_count"] == 100
        assert set(report["failed_checks"]).issubset(warnings)
    assert (bpy.data.filepath, bpy.context.scene.frame_current) == original
    print(
        json.dumps(
            {
                "snapshot_preserved_parent": True,
                "warnings": warnings,
                "bytes": Path(output).stat().st_size,
            }
        )
    )
finally:
    job.close()
