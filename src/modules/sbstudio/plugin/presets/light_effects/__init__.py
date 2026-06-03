"""Built-in light effect output presets for Skybrush Studio.

Functions are referenced by a stable string ID, so projects stay portable
across machines and operating systems (no .py file paths inside .blend).

A preset function returns a float in ``[0, 1]`` for the X/Y axis of the
color ramp / image lookup, given:

    def my_preset(frame, time_fraction, drone_index, formation_index,
                  position, drone_count) -> float: ...

Display names follow the format ``<number><human-readable name>``,
e.g. ``「1」 Odd-Even Pulse`` (English) / ``①奇偶脉冲`` (Chinese). The number is
assigned by registration order across all categories.
"""

from __future__ import annotations

from .base import (
    get_preset_enum_items,
    get_preset_function,
    get_preset_mapping,
    register_preset,
)

__all__ = (
    "get_preset_function",
    "get_preset_enum_items",
    "register_preset",
    "register",
    "unregister",
)

# Import light effect presets to register them and include them in the enum items list.
from ..light_effects import (
    basic,  # noqa: F401
    chasing_tails,  # noqa: F401
    filling,  # noqa: F401
    generic,  # noqa: F401
    groups,  # noqa: F401
    radar_scan,  # noqa: F401
    radial,  # noqa: F401
    sweep,  # noqa: F401
    wave,  # noqa: F401
)

# ---------------------------------------------------------------------------
# Translations (registered with bpy.app.translations)
# ---------------------------------------------------------------------------


_I18N_DOMAIN = "sbstudio_light_fx_presets"


BlenderTranslationDict = dict[tuple[str, str], str]


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
    # Display = 「N」+ English label.  We translate the whole composite source.
    # Order is reversed (v5.1 effects first)
    reversed_presets = list(reversed(list(get_preset_mapping().items())))
    for i, (_preset_id, meta) in enumerate(reversed_presets):
        prefix = f"「{i + 1}」"
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
        print(f"[sbstudio.light_fx_presets] failed to register i18n: {exc}")


def unregister() -> None:
    try:
        import bpy
    except ImportError:
        return

    try:
        bpy.app.translations.unregister(_I18N_DOMAIN)
    except Exception:
        pass
