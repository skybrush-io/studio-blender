from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON_PATH = ROOT / "src" / "addons" / "ui_dronetara_studio.py"


def _read(path: str | Path) -> str:
    return (ROOT / path).read_text() if isinstance(path, str) else path.read_text()


def _addon_info() -> dict[str, object]:
    tree = ast.parse(ADDON_PATH.read_text())
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
        if visible_skybrush.search(path.read_text())
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
    addon = ADDON_PATH.read_text()
    assert "Scene.skybrush" in addon
    assert "Object.skybrush" in addon

    operators = _read("src/modules/sbstudio/plugin/operators/export_to_csv.py")
    assert 'bl_idname = "export_scene.skybrush_csv"' in operators
