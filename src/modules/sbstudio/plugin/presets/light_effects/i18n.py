from typing import TypeAlias

from .base import iter_preset_mapping

__all__ = ("register", "unregister")

_I18N_DOMAIN = "sbstudio_light_fx_presets"


BlenderTranslationDict: TypeAlias = dict[tuple[str, str], str]


def _build_translation_dict() -> dict[str, BlenderTranslationDict]:
    """Build a Blender-compatible translation dict.  Maps each English source
    string used in the UI to its Chinese and Japanese translations."""
    zh: BlenderTranslationDict = {}
    ja: BlenderTranslationDict = {}

    # Translate the OUTPUT_ITEMS entry "Light preset"
    zh[("*", "Light preset")] = "灯光模版"
    zh[("*", "Built-in light effect preset (portable across machines)")] = (
        "内置灯效预设（跨电脑/系统可移植，不依赖 .py 文件路径）"
    )
    zh[("*", "Light Preset")] = "灯光模版"
    zh[("*", "Preset")] = "预设"

    ja[("*", "Light preset")] = "ライトプリセット"
    ja[("*", "Built-in light effect preset (portable across machines)")] = (
        "内蔵ライトエフェクトプリセット（マシン間でポータブル）"
    )
    ja[("*", "Light Preset")] = "ライトプリセット"
    ja[("*", "Preset")] = "プリセット"

    # Translate each preset's display string.
    for index, meta in enumerate(iter_preset_mapping(), 1):
        prefix = f"「{index}」"
        en_display = f"{prefix}{meta.label}"
        zh_display = f"{prefix}{meta.translations.get('zh', meta.label)}"
        ja_display = f"{prefix}{meta.translations.get('ja', meta.label)}"
        zh[("*", en_display)] = zh_display
        ja[("*", en_display)] = ja_display

    return {"zh_HANS": zh, "zh_CN": zh, "ja_JP": ja}


def register() -> None:
    """Register translations for the built-in light effect presets.

    Called by the addon's top-level ``register()`` function.  Idempotent.
    """
    try:
        import bpy
    except ImportError:
        return  # Headless / unit-test context

    try:
        bpy.app.translations.unregister(_I18N_DOMAIN)
    except Exception:
        pass  # not previously registered

    try:
        bpy.app.translations.register(_I18N_DOMAIN, _build_translation_dict())
    except Exception as exc:
        # Translation is non-critical; log and move on so the addon still loads.
        print(
            f"[sbstudio.plugin.presets.light_effects.i18n] failed to register i18n: {exc}"
        )


def unregister() -> None:
    try:
        import bpy
    except ImportError:
        return

    try:
        bpy.app.translations.unregister(_I18N_DOMAIN)
    except Exception as exc:
        # Translation is non-critical; log and move on
        print(
            f"[sbstudio.plugin.presets.light_effects.i18n] failed to unregister i18n: {exc}"
        )
