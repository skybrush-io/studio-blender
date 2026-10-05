"""Modal lifecycle with UI test doubles, NOT live keyboard/Blender acceptance."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from sbstudio.background_job import BackgroundExportJob


@pytest.fixture
def modal_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "bpy", ModuleType("bpy"))
    monkeypatch.setitem(
        sys.modules,
        "sbstudio.plugin.background_worker",
        ModuleType("sbstudio.plugin.background_worker"),
    )
    prefs = ModuleType("sbstudio.plugin.model.global_settings")
    prefs.get_preferences = lambda: SimpleNamespace(operation_mode="OFFLINE")
    monkeypatch.setitem(sys.modules, prefs.__name__, prefs)
    source = (
        Path(__file__).resolve().parents[1]
        / "src/modules/sbstudio/plugin/operators/native_background.py"
    )
    spec = importlib.util.spec_from_file_location("native_lifecycle_under_test", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "outcome",
    ["success", "warning", "checked", "preview", "cancel", "crash", "changed"],
)
def test_modal_completion_and_cleanup(modal_module, tmp_path, outcome):
    reports, status, removed_timers = [], [], []
    target = tmp_path / "show.skyc"
    target.write_bytes(b"old")
    job = BackgroundExportJob(target)
    directory = job.directory
    job.process = SimpleNamespace(poll=lambda: 1 if outcome == "crash" else 0)
    job.artifact.write_bytes(b"new")
    (directory / "result.json").write_text(
        json.dumps(
            {
                "success": True,
                "warnings": ["separation"] if outcome == "warning" else [],
                "export_gate": {
                    "status": "passed_implemented_checks"
                    if outcome == "checked"
                    else "preview_only"
                }
                if outcome in {"checked", "preview"}
                else None,
            }
        )
    )
    operator = SimpleNamespace(
        _background_job=job,
        _background_timer="owned timer",
        report=lambda level, message: reports.append((level, message)),
    )
    context = SimpleNamespace(
        window_manager=SimpleNamespace(event_timer_remove=removed_timers.append),
        workspace=SimpleNamespace(status_text_set=status.append),
    )
    modal_module._active_job = job
    try:
        if outcome == "cancel":
            assert modal_module.modal(
                operator, context, SimpleNamespace(type="ESC", value="PRESS")
            ) == {"RUNNING_MODAL"}
            assert job.cancelled_at is not None
        elif outcome == "changed":
            target.write_bytes(b"changed externally")
        result = modal_module.modal(
            operator, context, SimpleNamespace(type="TIMER", value="NOTHING")
        )
        success = outcome in {"success", "warning", "checked", "preview"}
        assert result == ({"FINISHED"} if success else {"CANCELLED"})
        assert target.read_bytes() == (
            b"new"
            if success
            else b"changed externally"
            if outcome == "changed"
            else b"old"
        )
        assert reports[-1][0] == (
            {"WARNING"}
            if outcome in {"warning", "preview"}
            else {"INFO"}
            if outcome in {"success", "checked", "cancel"}
            else {"ERROR"}
        )
        if outcome == "checked":
            assert "independent flight review" in reports[-1][1]
        elif outcome == "preview":
            assert "PREVIEW ONLY" in reports[-1][1]
        assert removed_timers == ["owned timer"]
        assert status[-1] is None
        assert operator._background_job is None
        assert modal_module._active_job is None
        assert not directory.exists()
    finally:
        job.close()
