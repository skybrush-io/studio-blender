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
    "get_preset_id_from_legacy_enum_value",
    "iter_preset_mapping",
    "preset_id_exists",
    "register_preset",
    "LEGACY_PRESET_IDS_5_0_4",
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


# ---------------------------------------------------------------------------
# Legacy (pre-5.1) integer preset storage
# ---------------------------------------------------------------------------


LEGACY_PRESET_IDS_5_0_4: tuple[str, ...] = (
    "odd_even_pulse",
    "odd_even_constant",
    "simple_filling",
    "chasing_tails_x",
    "chasing_tails_y",
    "chasing_tails_z",
    "clover_fill",
    "continuous_filling_1",
    "continuous_filling_1_5",
    "continuous_filling_2",
    "continuous_filling_3",
    "continuous_filling_4",
    "continuous_filling_5",
    "continuous_filling_stripes",
    "lightfx_0",
    "lightfx_1",
    "lightfx_4",
    "lightfx_6",
    "lightfx_7",
    "lightfx_8",
    "group_ranges_3",
    "group_ranges_5",
    "radar_scan",
    "radar_scan_2",
    "radar_scan_3",
    "radar_scan_4",
    "radar_scan_5",
    "continuous_radar_scan_test",
    "paint_on_test_1",
    "paint_on_test_2",
    "paint_on_test_3",
    "radial_diffusion",
    "radial_diffusion_2",
    "radial_diffusion_3",
    "radial_convergence",
    "radial_convergence_2",
    "radial_convergence_3",
    "sweep_positive_x",
    "sweep_positive_y",
    "sweep_positive_z",
    "sweep_negative_x",
    "sweep_negative_y",
    "sweep_negative_z",
    "sweep_positive_x_off",
    "sweep_positive_y_off",
    "sweep_positive_z_off",
    "sweep_negative_x_off",
    "sweep_negative_y_off",
    "sweep_negative_z_off",
    "radial_sweep_on",
    "radial_sweep_off",
    "radial_sweep_on_2",
    "radial_sweep_off_2",
    "wave_sawtooth",
    "wave_sawtooth_2",
    "wave_sawtooth_3",
    "wave_triangle",
    "expanding_pulse",
    "sawtooth_pulse",
    "spatial_wave",
    "spatial_wave_2",
)
"""Registration order of the presets in Skybrush Studio for Blender 5.0.4
(tag ``5.0.4``, commit ``4df6a1e``, dated 2026-09-22). This is therefore the
last released version that stored ``LightEffect.preset_id`` as an enum value.
Every release that stored ``preset_id`` as an integer (5.0.0 to 5.0.4
inclusive) registered the presets in exactly this order; earlier releases
never saved ``preset_id`` at all.

This is a frozen record of history; do not update it when the registration
order of the presets changes.  Note that ``paint_on_test_3`` was removed
afterwards (commit ``72024c8c``, 2026-10-15), so legacy values from slot 31
onwards refer to the slots shifted by one with respect to the current
registration order."""


def get_preset_id_from_legacy_enum_value(value: int) -> str:
    """Maps a raw integer ``LightEffect.preset_id`` value to a preset ID string.

    Up to Skybrush Studio for Blender 5.0.4 (tag ``5.0.4``, commit
    ``4df6a1e``, 2026-09-22), the preset was an ``EnumProperty`` stored as an
    integer: ``0`` = ``<None>`` (which was the first item back then) and ``k``
    (one-based) = the k-th registered preset.  The mapping goes through the
    frozen registration order of 5.0.4 (see :data:`LEGACY_PRESET_IDS_5_0_4`)
    because presets have been removed since, which shifted the later slots.

    Values outside the range of the table map to the null preset. Values
    inside the range are returned as-is, _even_ if the mapped preset is not
    registered in the current version of the add-on (e.g. because it was
    removed at a later point), so the migration keeps the original preset
    reference instead of losing it.

    The table covers every release that stored ``preset_id`` as an integer:
    all of 5.0.0 to 5.0.4 used this exact order, and the integer storage did
    not exist before 5.0.0 because the preset system was introduced by commit
    ``69304996`` (2026-07-17), first shipped in ``5.0.0`` (2026-07-24). Files
    saved by older releases therefore contain no ``preset_id`` values at all.
    Files saved by unreleased development revisions in between may have
    registered the presets in another order and are not mapped reliably
    either.
    """
    legacy = LEGACY_PRESET_IDS_5_0_4
    if value <= 0 or value > len(legacy):
        return NULL_PRESET_ID
    return legacy[value - 1]
