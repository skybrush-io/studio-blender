from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, MutableMapping, Sequence

if TYPE_CHECKING:
    from sbstudio.plugin.model.light_effects import LightEffectOutputFunctionV2

__all__ = (
    "get_preset_enum_index",
    "get_preset_enum_items",
    "get_preset_function",
    "iter_preset_mapping",
    "preset_id_exists",
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
        if id == NULL_PRESET_ID:
            raise ValueError(f"Preset ID {id!r} is reserved for the null preset")
        if any(meta.label == label for meta in _PRESETS.values()):
            raise ValueError(f"Duplicate light effect preset label: {label!r}")
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


def preset_id_exists(preset_id: str) -> bool:
    """Return whether the given preset ID is known to this version of the add-on;
    either the null preset or the ID of a registered preset."""
    return preset_id == NULL_PRESET_ID or preset_id in _PRESETS


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
    items: list[tuple[str, str, str]] = []
    for index, meta in enumerate(iter_preset_mapping(), 1):
        prefix = f"[{index}] "
        display = f"{prefix}{meta.label}"
        items.append((meta.id, display, meta.description or meta.label))
    # The null preset must come last: Blender's number-key navigation in the
    # dropdown is positional, so a leading <None> entry would shift every
    # preset down and pressing "5" would select the preset labeled "[4]".
    items.append((NULL_PRESET_ID, "<None>", "None"))
    return items


# Module-level cache.  *** DO NOT *** rebuild this per call.
_CACHED_ENUM_ITEMS: list[tuple[str, str, str]] | None = None
_CACHED_ENUM_INDEXES: dict[str, int] | None = None


def get_preset_enum_items() -> list[tuple[str, str, str]]:
    """Returns the (cached) enum items list, building it on first access."""
    global _CACHED_ENUM_ITEMS
    if _CACHED_ENUM_ITEMS is None:
        _CACHED_ENUM_ITEMS = _build_enum_items()
    return _CACHED_ENUM_ITEMS


def get_preset_enum_index(preset_id: str) -> int:
    """Returns the index of the given preset ID in the cached enum items list.

    Returns the index of the null preset (the last item) when the ID is empty
    or unknown to this version of the add-on, so unknown IDs are displayed as
    ``<None>`` in the UI dropdown instead of raising or resetting the stored
    string.
    """
    global _CACHED_ENUM_INDEXES
    if _CACHED_ENUM_INDEXES is None:
        _CACHED_ENUM_INDEXES = {
            item_id: index
            for index, (item_id, _, _) in enumerate(get_preset_enum_items())
        }
    return _CACHED_ENUM_INDEXES.get(preset_id, _CACHED_ENUM_INDEXES[NULL_PRESET_ID])

