"""Unit tests for the background Viewer load in ValidateTrajectoriesOperator.

Blender (bpy) is not available here, so the operator module is loaded with
stubbed bpy and stubbed sibling modules; the real viewer_bridge is used.
"""

import importlib.util
import sys
import threading
import time
import types
from pathlib import Path
from unittest import mock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "modules"


def _load_module(name, path):
    """Loads a module from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stub(name, **attrs):
    """Creates a stub module with the given attributes."""
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


@pytest.fixture(scope="module")
def operator_module():
    """Loads the operator module with stubbed bpy and siblings."""
    names = [
        "bpy",
        "bpy.props",
        "bpy.types",
        "sbstudio",
        "sbstudio.plugin",
        "sbstudio.plugin.operators",
        "sbstudio.plugin.props",
        "sbstudio.plugin.tasks",
        "sbstudio.plugin.utils",
        "sbstudio.model",
        "sbstudio.viewer_bridge",
        "sbstudio.model.safety_check",
        "sbstudio.plugin.api",
        "sbstudio.plugin.props.frame_range",
        "sbstudio.plugin.tasks.light_effects",
        "sbstudio.plugin.tasks.safety_check",
        "sbstudio.plugin.utils.sampling",
        "sbstudio.plugin.operators.utils",
        "sbstudio.plugin.operators.validate_trajectories",
    ]
    original = {name: sys.modules.get(name) for name in names}

    # Stub bpy
    bpy = _stub("bpy")
    bpy.data = types.SimpleNamespace(filepath="")

    class FakeOperator:
        """A minimal stand-in for bpy.types.Operator."""

        def report(self, level, message):
            """Records the reported level and message."""
            self._reported = (level, message)

    bpy_props = _stub("bpy.props", BoolProperty=lambda **kw: None)
    bpy_types = _stub("bpy.types", Context=object, Operator=FakeOperator)
    bpy.props = bpy_props
    bpy.types = bpy_types

    # Stub sbstudio packages as namespaces so the real viewer_bridge loads
    for pkg in (
        "sbstudio",
        "sbstudio.plugin",
        "sbstudio.plugin.operators",
        "sbstudio.plugin.props",
        "sbstudio.plugin.tasks",
        "sbstudio.plugin.utils",
        "sbstudio.model",
    ):
        module = types.ModuleType(pkg)
        module.__path__ = []
        sys.modules[pkg] = module

    # Real viewer_bridge
    _load_module("sbstudio.viewer_bridge", SRC / "sbstudio" / "viewer_bridge.py")

    # Stub the operator's other imports
    _stub("sbstudio.model.safety_check", SafetyCheckParams=object)
    _stub(
        "sbstudio.plugin.api",
        call_api_from_blender_operator=mock.MagicMock(),
    )
    _stub(
        "sbstudio.plugin.props.frame_range",
        FrameRangeProperty=lambda: None,
        resolve_frame_range=lambda *a: None,
    )
    _stub(
        "sbstudio.plugin.tasks.light_effects",
        suspended_light_effects=mock.MagicMock(),
    )
    _stub(
        "sbstudio.plugin.tasks.safety_check",
        suspended_safety_checks=mock.MagicMock(),
    )
    _stub(
        "sbstudio.plugin.utils.sampling",
        sample_positions_of_objects_in_frame_range=mock.MagicMock(),
    )
    _stub(
        "sbstudio.plugin.operators.utils",
        get_drones_to_export=mock.MagicMock(return_value=[]),
    )

    module = _load_module(
        "sbstudio.plugin.operators.validate_trajectories",
        SRC / "sbstudio" / "plugin" / "operators" / "validate_trajectories.py",
    )
    yield module
    for name in names:
        if original[name] is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original[name]


def _operator(operator_module):
    """Builds a fresh operator instance."""
    return operator_module.ValidateTrajectoriesOperator()


def test_background_load_success(operator_module):
    """A successful load reports FINISHED."""
    op = _operator(operator_module)
    with mock.patch.object(operator_module.skybrush_viewer, "load_show_for_validation"):
        op._load_show_in_background(b"data", filename=None)
    assert op._load_outcome[0] == "FINISHED"
    assert "Viewer window" in op._load_outcome[1]


def test_background_load_not_found(operator_module):
    """A missing Viewer reports CANCELLED with a not-running message."""
    op = _operator(operator_module)
    from sbstudio.viewer_bridge import SkybrushViewerNotFoundError

    with mock.patch.object(
        operator_module.skybrush_viewer,
        "load_show_for_validation",
        side_effect=SkybrushViewerNotFoundError(),
    ):
        op._load_show_in_background(b"data", filename=None)
    assert op._load_outcome[0] == "CANCELLED"
    assert "not running" in op._load_outcome[1]


def test_background_load_viewer_error(operator_module):
    """A Viewer error reports CANCELLED with its message."""
    op = _operator(operator_module)
    from sbstudio.viewer_bridge import SkybrushViewerError

    with mock.patch.object(
        operator_module.skybrush_viewer,
        "load_show_for_validation",
        side_effect=SkybrushViewerError("Timed out"),
    ):
        op._load_show_in_background(b"data", filename=None)
    assert op._load_outcome == ("CANCELLED", "Timed out")


def test_modal_reports_when_thread_finishes(operator_module):
    """modal() reports the outcome once the thread is done."""
    op = _operator(operator_module)
    op._load_outcome = ("FINISHED", "Now switch to the Skybrush Viewer window")
    op._load_thread = threading.Thread(target=lambda: None)
    op._load_thread.start()
    op._load_thread.join()
    op._load_timer = object()

    context = mock.Mock()
    event = types.SimpleNamespace(type="TIMER")
    assert op.modal(context, event) == {"FINISHED"}
    assert op._reported == ({"INFO"}, "Now switch to the Skybrush Viewer window")
    context.window_manager.event_timer_remove.assert_called_once_with(op._load_timer)


def test_modal_esc_cancels(operator_module):
    """ESC cancels the load and removes the timer."""
    op = _operator(operator_module)
    op._load_outcome = None
    op._load_thread = threading.Thread(target=lambda: None)
    op._load_timer = object()
    op._cancelled = threading.Event()

    context = mock.Mock()
    event = types.SimpleNamespace(type="ESC")
    assert op.modal(context, event) == {"CANCELLED"}
    assert op._cancelled.is_set()
    context.window_manager.event_timer_remove.assert_called_once_with(op._load_timer)


def test_modal_passes_through_unhandled_events(operator_module):
    """Unhandled events pass through while the load runs."""
    op = _operator(operator_module)
    op._load_thread = threading.Thread(target=lambda: None)
    op._load_timer = object()

    context = mock.Mock()
    event = types.SimpleNamespace(type="MOUSEMOVE")
    assert op.modal(context, event) == {"RUNNING_MODAL", "PASS_THROUGH"}
    context.window_manager.event_timer_remove.assert_not_called()


def test_background_load_skipped_when_cancelled(operator_module):
    """A cancelled load never sends the show."""
    op = _operator(operator_module)
    op._cancelled = threading.Event()
    op._cancelled.set()
    with mock.patch.object(
        operator_module.skybrush_viewer, "load_show_for_validation"
    ) as load:
        op._load_show_in_background(b"data", filename=None)
    load.assert_not_called()
    assert op._load_outcome[0] == "CANCELLED"


def _execute(operator_module, window, load_blocker=None):
    """Runs execute() with a mocked Viewer load.

    When load_blocker is given, the mocked load waits on it, so the test can
    assert execute() returns while the load is still blocked. The wait is
    bounded so a stuck load cannot hang the suite.
    """
    op = _operator(operator_module)
    context = mock.Mock()
    context.window = window
    context.scene.skybrush.safety_check = None
    context.scene.render.fps = 24
    context.scene.frame_start = 1

    api = mock.MagicMock()
    api.export.return_value = b"show"
    api_context = mock.MagicMock()
    api_context.__enter__.return_value = api
    api_context.__exit__.return_value = False

    with (
        mock.patch.object(operator_module, "resolve_frame_range", return_value=(1, 25)),
        mock.patch.object(
            operator_module, "SafetyCheckParams", return_value=mock.Mock()
        ),
        mock.patch.object(
            operator_module,
            "sample_positions_of_objects_in_frame_range",
            return_value={},
        ),
        mock.patch.object(
            operator_module.skybrush_viewer, "check_running", return_value=True
        ),
        mock.patch.object(
            operator_module,
            "call_api_from_blender_operator",
            return_value=api_context,
        ),
        mock.patch.object(
            operator_module.skybrush_viewer, "load_show_for_validation"
        ) as load,
    ):
        if load_blocker is not None:

            def _blocked_load(*args, **kwargs):
                """Blocks until the test releases it."""
                load_blocker.wait(timeout=5)

            load.side_effect = _blocked_load
        result = op.execute(context)
        if window is not None:
            if load_blocker is not None:
                # Wait (bounded) for the background thread to reach the load
                # while the patch is still active, so the load stays mocked.
                deadline = time.monotonic() + 2
                while load.call_count == 0 and time.monotonic() < deadline:
                    time.sleep(0.01)
            else:
                op._load_thread.join(timeout=5)
    return op, context, load, result


def test_execute_starts_background_load_and_returns_running_modal(operator_module):
    """execute() returns RUNNING_MODAL while the load is still blocked."""
    window = mock.Mock()
    blocker = threading.Event()
    op, context, load, result = _execute(operator_module, window, load_blocker=blocker)
    try:
        assert result == {"RUNNING_MODAL"}
        assert load.call_count == 1
        assert op._load_thread.is_alive()
        assert op._load_outcome is None
    finally:
        blocker.set()
    op._load_thread.join(timeout=5)
    assert not op._load_thread.is_alive()
    context.window_manager.event_timer_add.assert_called_once_with(0.1, window=window)
    context.window_manager.modal_handler_add.assert_called_once_with(op)
    load.assert_called_once_with(b"show", filename=None)
    assert op._load_outcome[0] == "FINISHED"


def test_execute_without_window_runs_synchronously(operator_module):
    """Without a window the load runs synchronously."""
    op, context, load, result = _execute(operator_module, None)
    assert result == {"FINISHED"}
    assert op._reported == (
        {"INFO"},
        "Now switch to the Skybrush Viewer window to view the results",
    )
    context.window_manager.event_timer_add.assert_not_called()
    context.window_manager.modal_handler_add.assert_not_called()
    load.assert_called_once_with(b"show", filename=None)
