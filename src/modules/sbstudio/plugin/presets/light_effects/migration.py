"""Migration related functionality for light effects."""

from __future__ import annotations

from typing import Any

from .base import NULL_PRESET_ID, preset_id_exists

_LEGACY_PRESET_IDS_5_0_4: tuple[str, ...] = (
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
    frozen registration order of 5.0.4 (see :data:`_LEGACY_PRESET_IDS_5_0_4`)
    because presets have been removed since, which shifted the later slots.

    The table covers every release that stored ``preset_id`` as an integer:
    all of 5.0.0 to 5.0.4 used this exact order, and the integer storage did
    not exist before 5.0.0 because the preset system was introduced by commit
    ``69304996`` (2026-07-17), first shipped in ``5.0.0`` (2026-07-24). Files
    saved by older releases therefore contain no ``preset_id`` values at all,
    and such files are left untouched by the migration. Files saved by
    unreleased development revisions in between may have registered the
    presets in another order and are not mapped reliably either.

    Legacy values that refer to a preset that no longer exists (e.g. the
    removed ``paint_on_test_3``) map to the null preset, mirroring the old
    fallback behavior where an unknown enum value read back as an empty
    string, i.e. no preset.
    """
    legacy = _LEGACY_PRESET_IDS_5_0_4
    if value <= 0 or value > len(legacy):
        return NULL_PRESET_ID
    preset_id = legacy[value - 1]
    return preset_id if preset_id_exists(preset_id) else NULL_PRESET_ID


def migrate_legacy_preset_id(effect: Any) -> bool:
    """Replaces a legacy integer ``preset_id`` of a light effect with the
    corresponding preset ID string, in place; see
    :func:`get_preset_id_from_legacy_enum_value` for the legacy format
    (Skybrush Studio for Blender 5.0.4 and earlier).

    When a file saved by such an old version is loaded, ``preset_id`` may
    still hold a raw integer; this function detects that and replaces it with
    the mapped preset ID string. It is a no-op if the stored value is already
    a string or missing.

    Returns:
        whether a conversion was performed
    """
    value = effect.get("preset_id")
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    preset_id = get_preset_id_from_legacy_enum_value(value)
    # The legacy value is stored as an integer ID property;
    # the fresh string ID property must be created from scratch
    # after removing the legacy one.
    del effect["preset_id"]
    effect["preset_id"] = preset_id
    return True
