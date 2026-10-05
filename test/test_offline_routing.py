"""Backend dispatch without Blender, sockets, service credentials or a license."""

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def routing(monkeypatch):
    # Model annotations reference Vector; these tests never evaluate vectors.
    mathutils = ModuleType("mathutils")

    class UnavailableVector:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Routing tests must not evaluate Blender vectors")

    mathutils.Vector = UnavailableVector
    monkeypatch.setitem(sys.modules, "mathutils", mathutils)
    # API gateway imports the pure progress module through a Blender-dependent
    # package initializer. Bypass only that initializer for these routing tests.
    utils = ModuleType("sbstudio.plugin.utils")
    utils.__path__ = [str(ROOT / "src/modules/sbstudio/plugin/utils")]
    monkeypatch.setitem(sys.modules, utils.__name__, utils)
    prefs = SimpleNamespace(operation_mode="OFFLINE", api_key="key", server_url="url")
    settings = ModuleType("sbstudio.plugin.model.global_settings")
    settings.get_preferences = lambda: prefs
    monkeypatch.setitem(sys.modules, settings.__name__, settings)
    constants = ModuleType("sbstudio.plugin.constants")
    constants.DEFAULT_SERVER_URL = "http://localhost:8000"
    monkeypatch.setitem(sys.modules, constants.__name__, constants)
    helpers = ModuleType("sbstudio.plugin.plugin_helpers")
    helpers.is_online_access_allowed = lambda: False
    monkeypatch.setitem(sys.modules, helpers.__name__, helpers)
    gateway = ModuleType("sbstudio.plugin.gateway")
    gateway.get_gateway_if_configured = lambda: pytest.fail("Unexpected gateway access")
    monkeypatch.setitem(sys.modules, gateway.__name__, gateway)
    spec = importlib.util.spec_from_file_location(
        "sbstudio.plugin.api", ROOT / "src/modules/sbstudio/plugin/api.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module, prefs


def test_offline_works_with_online_access_disabled(routing, monkeypatch):
    api, prefs = routing

    def forbidden(*args, **kwargs):
        pytest.fail("Offline dispatch touched remote API configuration")

    monkeypatch.setattr(api, "_get_api_settings", forbidden)
    monkeypatch.setattr(api, "_get_api_from_url_and_key", forbidden)
    assert isinstance(api.get_api(), api.LocalSkybrushStudioAPI)
    assert api.get_api().get_limits().num_drones == float("inf")


@pytest.mark.parametrize("mode", ["COMMUNITY", "LOCAL", "CLOUD", "ADVANCED"])
def test_server_modes_still_require_online_access(routing, monkeypatch, mode):
    api, prefs = routing
    prefs.operation_mode = mode
    calls = []
    monkeypatch.setattr(api, "_get_api_from_url_and_key", lambda **kw: calls.append(kw))
    with pytest.raises(api.NoOnlineAccessAllowedError):
        api.get_api()
    assert not calls


@pytest.mark.parametrize(
    "mode,settings",
    [
        ("COMMUNITY", {"url": "", "key": "key"}),
        ("LOCAL", {"url": "http://localhost:8000", "key": ""}),
        ("CLOUD", {"url": "", "key": "key"}),
        ("ADVANCED", {"url": "url", "key": "key"}),
    ],
)
def test_existing_server_configuration_is_preserved(
    routing, monkeypatch, mode, settings
):
    api, prefs = routing
    prefs.operation_mode = mode
    calls = []
    remote = object()
    monkeypatch.setattr(api, "is_online_access_allowed", lambda: True)
    monkeypatch.setattr(
        api, "_get_api_from_url_and_key", lambda **kw: calls.append(kw) or remote
    )
    assert api.get_api(check_version=False) is remote
    assert calls == [settings]
    prefs.operation_mode = "OFFLINE"
    assert isinstance(api.get_api(), api.LocalSkybrushStudioAPI)
    prefs.operation_mode = mode
    assert api.get_api(check_version=False) is remote


def test_remote_error_does_not_silently_fall_back_to_offline(routing, monkeypatch):
    from sbstudio.api.errors import SkybrushStudioAPIError

    api, prefs = routing
    prefs.operation_mode = "COMMUNITY"
    monkeypatch.setattr(api, "is_online_access_allowed", lambda: True)

    def unavailable(**kwargs):
        raise SkybrushStudioAPIError("service unavailable")

    monkeypatch.setattr(api, "_get_api_from_url_and_key", unavailable)
    with pytest.raises(SkybrushStudioAPIError, match="service unavailable"):
        api.get_api()


def test_offline_format_list_is_reset_when_switching_back(routing):
    from sbstudio.api.types import Limits
    from sbstudio.model.file_formats import (
        FileFormat,
        get_supported_file_formats,
        update_supported_file_formats_from_limits,
    )

    api, _ = routing
    try:
        update_supported_file_formats_from_limits(
            api.LocalSkybrushStudioAPI().get_limits()
        )
        assert set(get_supported_file_formats()) == {FileFormat.SKYC, FileFormat.CSV}
        update_supported_file_formats_from_limits(Limits(features=["export:plot"]))
        assert FileFormat.PDF in get_supported_file_formats()
    finally:
        update_supported_file_formats_from_limits(Limits())


def test_saved_operation_mode_values_and_default_are_preserved():
    source = ROOT / "src/modules/sbstudio/plugin/model/global_settings.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    setting = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "operation_mode"
    )
    options = {kw.arg: kw.value for kw in setting.value.keywords}
    items = ast.literal_eval(options["items"])
    # Blender serializes EnumProperty's implicit integer values by item order.
    assert [item[0] for item in items] == [
        "COMMUNITY",
        "LOCAL",
        "CLOUD",
        "ADVANCED",
        "OFFLINE",
    ]
    assert ast.literal_eval(options["default"]) == "COMMUNITY"
