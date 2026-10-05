"""Native modal lifecycle for process-isolated offline exports."""

import json
import sys
from pathlib import Path

import bpy

from sbstudio.background_job import BackgroundExportJob
from sbstudio.export_policy import offline_export_message
from sbstudio.plugin import background_worker
from sbstudio.plugin.model.global_settings import get_preferences

_active_job = None


def start(operator, context):
    global _active_job
    if _active_job is not None:
        operator.report({"ERROR"}, "Another background export is already running")
        return {"CANCELLED"}
    if get_preferences().operation_mode != "OFFLINE":
        operator.report(
            {"ERROR"}, "Background export is available only in Offline mode"
        )
        return {"CANCELLED"}
    if any(
        image.is_dirty and not image.packed_file
        for image in bpy.data.images
        if image.source in {"FILE", "GENERATED"}
    ):
        operator.report(
            {"ERROR"}, "Save or pack modified images before background export"
        )
        return {"CANCELLED"}
    if any(
        effect.is_animated for effect in context.scene.skybrush.light_effects.entries
    ):
        operator.report(
            {"ERROR"}, "Video-based light effects require foreground export"
        )
        return {"CANCELLED"}
    filepath = bpy.path.ensure_ext(operator.filepath, operator.filename_ext)
    if Path(filepath).name.lower() == operator.filename_ext.lower():
        operator.report({"ERROR"}, "Filename must not be empty")
        return {"CANCELLED"}
    job = BackgroundExportJob(filepath)
    operator._background_job = job
    operator._background_timer = None
    try:
        module = sys.modules["ui_skybrush_studio"]
        if module.__file__ is None:
            raise RuntimeError("Cannot locate the installed add-on")
        settings = {
            "export_selected": operator.export_selected,
            "frame_range": operator.frame_range,
            **operator.get_settings(),
            "redraw": False,
        }
        snapshot = job.directory / "snapshot.blend"
        status = bpy.ops.wm.save_as_mainfile(
            filepath=str(snapshot),
            copy=True,
            relative_remap=True,
            check_existing=False,
            compress=False,
        )
        if status != {"FINISHED"}:
            raise RuntimeError("Could not snapshot the scene")
        config = {
            "addon_directory": str(Path(module.__file__).parent),
            "addon_module": module.__name__,
            "settings": settings,
            "snapshot": str(snapshot),
            "artifact": str(job.artifact),
            "format": operator.get_format().value,
            "scene": context.scene.name,
            "view_layer": context.view_layer.name,
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
        _active_job = job
        operator._background_timer = context.window_manager.event_timer_add(
            0.2, window=context.window
        )
        context.window_manager.modal_handler_add(operator)
        context.workspace.status_text_set(
            "Skybrush: exporting scene snapshot. Press Esc to cancel."
        )
        return {"RUNNING_MODAL"}
    except Exception as exc:
        cleanup(operator, context)
        operator.report({"ERROR"}, str(exc))
        return {"CANCELLED"}


def cleanup(operator, context):
    global _active_job
    timer = getattr(operator, "_background_timer", None)
    if timer is not None:
        context.window_manager.event_timer_remove(timer)
        operator._background_timer = None
    job = getattr(operator, "_background_job", None)
    if job is not None:
        job.close()
        if _active_job is job:
            _active_job = None
        operator._background_job = None
    context.workspace.status_text_set(None)


def modal(operator, context, event):
    job = operator._background_job
    if event.type == "ESC" and event.value == "PRESS":
        job.cancel()
        context.workspace.status_text_set(
            "Skybrush: cancelling export; destination unchanged."
        )
        return {"RUNNING_MODAL"}
    if event.type != "TIMER":
        return {"PASS_THROUGH"}
    code = job.poll()
    if code is None:
        return {"RUNNING_MODAL"}
    try:
        if job.cancelled_at is not None:
            operator.report({"INFO"}, "Export cancelled; destination unchanged")
            return {"CANCELLED"}
        if code != 0:
            raise RuntimeError(job.error_message())
        warnings = job.commit()
        if job.export_gate is not None:
            operator.report(
                *offline_export_message(
                    job.destination,
                    {
                        "export_gate": job.export_gate,
                        "failed_checks": warnings,
                    },
                )
            )
        elif warnings:
            operator.report(
                {"WARNING"}, "Draft saved with warnings: " + ", ".join(warnings)
            )
        else:
            operator.report(
                {"INFO"}, f"Draft saved to {job.destination}; not flight clearance"
            )
        return {"FINISHED"}
    except Exception as exc:
        operator.report({"ERROR"}, str(exc))
        return {"CANCELLED"}
    finally:
        cleanup(operator, context)
