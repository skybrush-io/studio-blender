"""Prepare an isolated GUI session; UI actions are performed by the tester.

The timer only records state. It never sends keys, starts exports or changes
export behavior, so an observed cancellation must come through the real UI.
"""

import json
import sys
from pathlib import Path

import bpy

config = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text())
root = Path(config["root"])
bpy.ops.preferences.addon_enable(module="ui_skybrush_studio")

from sbstudio.plugin.model.global_settings import get_preferences
from sbstudio.plugin.operators import native_background

prefs = get_preferences()
prefs.operation_mode = "OFFLINE"
prefs.gateway_url = ""
# Remap relative asset paths when saving the new QA copy.
bpy.ops.wm.open_mainfile(filepath=config["source"], use_scripts=False)
bpy.ops.wm.save_as_mainfile(
    filepath=config["fixture"], relative_remap=True, check_existing=False
)
bpy.context.scene.name = "Skybrush GUI QA"
bpy.context.preferences.view.show_splash = False


def record_state():
    job = native_background._active_job
    state = {
        "blender_version": bpy.app.version_string,
        "filepath": bpy.data.filepath,
        "frame": bpy.context.scene.frame_current,
        "active_job": job is not None,
    }
    if job is not None:
        state.update(
            destination=str(job.destination),
            temporary_directory=str(job.directory),
            worker_pid=job.process.pid if job.process else None,
            cancelled=job.cancelled_at is not None,
        )
    (root / "gui-state.json").write_text(json.dumps(state, indent=2))
    return 0.5


bpy.app.timers.register(record_state, first_interval=0.5)
print("GUI QA READY: " + str(root), flush=True)
