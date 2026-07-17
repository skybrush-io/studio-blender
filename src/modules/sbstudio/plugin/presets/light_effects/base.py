from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, MutableMapping, Sequence

if TYPE_CHECKING:
    from bpy.types import Context

    from sbstudio.plugin.model.light_effects import LightEffectOutputFunctionV2

__all__ = (
    "get_preset_enum_items",
    "get_preset_function",
    "iter_preset_mapping",
    "register_preset",
    "NULL_PRESET_ID",
)


@dataclass(frozen=True)
class PresetMeta:
    id: str
    label: str  # English label (used as the i18n source string)
    function: LightEffectOutputFunctionV2
    description: str = ""
    translations: dict[str, str] = field(default_factory=dict)  # language code -> label


_PRESETS: MutableMapping[str, PresetMeta] = OrderedDict()
"""Insertion-ordered.  Order here = order in the UI dropdown = circled number."""

NULL_PRESET_ID: Final[str] = "_null"
"""Special preset ID for the case when a preset is not selected. Note that it cannot be
an empty string because Blender filters those.
"""


def register_preset(
    *,
    id: str,
    label: str,
    description: str = "",
    translations: Sequence[tuple[str, str]] = (),
):
    def decorator(fn: LightEffectOutputFunctionV2) -> LightEffectOutputFunctionV2:
        if id in _PRESETS:
            raise ValueError(f"Duplicate light effect preset ID: {id!r}")
        _PRESETS[id] = PresetMeta(
            id=id,
            label=label,
            function=fn,
            description=description,
            translations=dict(translations),
        )
        return fn

    return decorator


def get_preset_function(preset_id: str) -> LightEffectOutputFunctionV2 | None:
    meta = _PRESETS.get(preset_id)
    return meta.function if meta is not None else None


def iter_preset_mapping() -> Iterator[PresetMeta]:
    """Iterate over the preset metadata in registration order (which is the order
    they appear in the UI dropdown)."""
    return iter(_PRESETS.values())


# ---------------------------------------------------------------------------
# UI items list (built ONCE, kept alive at module level forever)
# ---------------------------------------------------------------------------


# CRITICAL: Per the Blender Python API docs, the items list returned from an
# ``EnumProperty`` ``items=`` callback MUST keep its strings alive for as long
# as the EnumProperty is registered, otherwise Blender will read freed memory
# and crash / hang (very visible on macOS).  We therefore build the items list
# ONCE at module load time and store it in ``_CACHED_ENUM_ITEMS``; the
# callback returns that single list reference forever.


def _build_enum_items() -> list[tuple[str, str, str]]:
    """Build the EnumProperty items list ONCE.  The returned list (and all of
    its strings) live for the entire lifetime of the addon, which is required
    by Blender to avoid use-after-free on the C side.

    Numbering format: 「1」「2」「3」... (full-width brackets)
    Order: v5.1 custom effects first, then original effects (reversed order)
    """
    items: list[tuple[str, str, str]] = [(NULL_PRESET_ID, "<None>", "None")]
    for index, meta in enumerate(iter_preset_mapping(), 1):
        # Use full-width brackets 「」 for numbering
        prefix = f"「{index}」"
        display = f"{prefix}{meta.label}"
        items.append((meta.id, display, meta.description or meta.label))
    return items


# Module-level cache.  *** DO NOT *** rebuild this per call.
_CACHED_ENUM_ITEMS: list[tuple[str, str, str]] | None = None


def get_preset_enum_items(self, context: Context) -> Sequence[tuple[str, str, str]]:
    """``items`` callback for the ``preset_id`` EnumProperty.

    Returns the same cached list every call.  Strings inside the list stay
    alive as long as the module is loaded, which prevents the well-known
    Blender crash / freeze caused by GC'd item strings (very visible on
    macOS in Material Preview mode)."""
    global _CACHED_ENUM_ITEMS
    if _CACHED_ENUM_ITEMS is None:
        _CACHED_ENUM_ITEMS = _build_enum_items()
    return _CACHED_ENUM_ITEMS
