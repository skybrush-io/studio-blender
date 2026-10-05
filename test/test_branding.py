from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADDON_PATH = ROOT / "src" / "addons" / "ui_dronetara_studio.py"


def _read(path: str | Path) -> str:
    resolved = ROOT / path if isinstance(path, str) else path
    return resolved.read_text(encoding="utf-8")


def _addon_info() -> dict[str, object]:
    tree = ast.parse(_read(ADDON_PATH))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "bl_info"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, dict)
            return value
    raise AssertionError("bl_info was not found in the Dronetara add-on")


def test_primary_addon_and_distribution_use_dronetara_name() -> None:
    assert ADDON_PATH.is_file()
    assert not (ROOT / "src" / "addons" / "ui_skybrush_studio.py").exists()

    info = _addon_info()
    assert info["name"] == "Dronetara Studio"
    assert info["author"] == "Dronetara"

    pyproject = _read("pyproject.toml")
    assert 'name = "dronetara-studio-for-blender"' in pyproject

    build_script = _read("etc/scripts/create_blender_dist.sh")
    assert "src/addons/ui_dronetara_studio.py" in build_script
    assert "src/addons/ui_skybrush_studio.py" not in build_script


def test_blender_preferences_and_visible_ui_use_dronetara_brand() -> None:
    preferences = _read("src/modules/sbstudio/plugin/model/global_settings.py")
    assert 'ADDON_MODULE_ID = "ui_dronetara_studio"' in preferences
    assert 'LEGACY_ADDON_MODULE_ID = "ui_skybrush_studio"' in preferences
    assert "for addon_id in (ADDON_MODULE_ID, LEGACY_ADDON_MODULE_ID)" in preferences

    live_sources = [
        *sorted((ROOT / "src" / "addons").glob("*.py")),
        *sorted((ROOT / "src" / "modules" / "sbstudio" / "plugin").rglob("*.py")),
    ]
    visible_skybrush = re.compile(
        r'(?:bl_label|bl_category)\s*=\s*"[^"]*Skybrush|'
        r'(?:text|name)\s*=\s*"[^"]*Skybrush'
    )
    offenders = [
        str(path.relative_to(ROOT))
        for path in live_sources
        if visible_skybrush.search(_read(path))
    ]
    assert offenders == []


def test_user_facing_brand_files_are_renamed() -> None:
    expected = (
        "assets/icons/linux/dronetara.png",
        "assets/icons/mac/dronetara.icns",
        "assets/icons/win/dronetara.ico",
        "doc/modules/ROOT/pages/panels/dronetara.adoc",
        "doc/modules/ROOT/pages/panels/dronetara",
        "src/addons/io_import_dronetara_all.py",
        "src/addons/io_import_dronetara_sky.py",
    )
    legacy = (
        "assets/icons/linux/skybrush.png",
        "assets/icons/mac/skybrush.icns",
        "assets/icons/win/skybrush.ico",
        "doc/modules/ROOT/pages/panels/skybrush.adoc",
        "doc/modules/ROOT/pages/panels/skybrush",
        "src/addons/io_import_skybrush_all.py",
        "src/addons/io_import_skybrush_sky.py",
    )

    assert all((ROOT / path).exists() for path in expected)
    assert not any((ROOT / path).exists() for path in legacy)


def test_legacy_blender_data_identifiers_remain_compatible() -> None:
    addon = _read(ADDON_PATH)
    assert "Scene.skybrush" in addon
    assert "Object.skybrush" in addon

    operators = _read("src/modules/sbstudio/plugin/operators/export_to_csv.py")
    assert 'bl_idname = "export_scene.skybrush_csv"' in operators


@pytest.fixture
def legacy_windows_text_default(monkeypatch):
    """Reproduce implicit cp1252 decoding without depending on the host locale."""
    read_text = Path.read_text

    def read_with_windows_default(self, encoding=None, errors=None, **kwargs):
        return read_text(self, encoding=encoding or "cp1252", errors=errors, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_with_windows_default)


def test_source_reader_preserves_utf8_with_windows_default(
    tmp_path, monkeypatch, legacy_windows_text_default
):
    source = tmp_path / "unicode.py"
    contents = '# Dronetara: \u014d, \u0921\u094d\u0930\u094b\u0928\r\nname = "Dronetara Studio"\r\n'
    source.write_bytes(contents.encode("utf-8"))
    with pytest.raises(UnicodeDecodeError):
        source.read_text()
    monkeypatch.setitem(_read.__globals__, "ROOT", tmp_path)
    expected = contents.replace("\r\n", "\n")
    assert _read("unicode.py") == expected
    assert _read(source) == expected


def test_branding_checks_work_with_windows_default(legacy_windows_text_default):
    test_primary_addon_and_distribution_use_dronetara_name()
    test_blender_preferences_and_visible_ui_use_dronetara_brand()
    test_legacy_blender_data_identifiers_remain_compatible()
