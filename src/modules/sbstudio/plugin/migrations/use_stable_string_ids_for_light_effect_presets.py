"""Migration to store light effect presets by stable string identifiers."""

from __future__ import annotations

from logging import Logger
from typing import Any, Iterator

import bpy
from bpy.types import Context

from sbstudio.plugin.presets.light_effects.base import (
    get_preset_id_from_legacy_enum_value,
)

from .base import Migration

__all__ = (
    "UseStableStringIdsForLightEffectPresetsMigration",
    "migrate_legacy_preset_id",
)


def _iter_light_effects() -> Iterator[Any]:
    """Iterates over all light effects in all loaded scenes."""
    for scene in bpy.data.scenes:
        show = getattr(scene, "skybrush", None)
        if show is None:
            continue
        for effect in show.light_effects.entries:
            yield effect


def _get_legacy_integer_preset_id(effect: Any) -> int | None:
    """Returns the raw legacy integer ``preset_id`` stored in the given light
    effect, or ``None`` when the effect does not store a legacy integer value
    (either because it is absent or because it is already in the new, string
    storage format).
    """
    value = effect.get("preset_id")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


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
    legacy_value = _get_legacy_integer_preset_id(effect)
    if legacy_value is None:
        return False
    preset_id = get_preset_id_from_legacy_enum_value(legacy_value)
    # The legacy value is stored as an integer ID property; assigning a string
    # to it in one step raises "Cannot assign a 'str' value to the existing
    # 'preset_id' Int IDProperty", so the fresh string ID property must be
    # created from scratch after removing the legacy one.
    del effect["preset_id"]
    effect["preset_id"] = preset_id
    return True


class UseStableStringIdsForLightEffectPresetsMigration(Migration):
    """Upgrades old Skybrush Studio for Blender file content (up to 5.0.4)
    that references the presets of light effects by their position in the
    registration order to a new version that stores stable, human-readable
    string identifiers instead. Position-based references break silently when
    the list of available presets changes between releases.
    """

    label = "Update light effect presets to stable identifiers"
    description = (
        "Upgrade your old (<= 5.0.4) Skybrush Studio for Blender file content\n"
        "so that light effects refer to their presets by their stable string\n"
        "identifier instead of their position in the registration order."
    )
    version_range = (2, 3)

    @classmethod
    def needs_migration(cls, context: Context) -> bool:
        """Returns whether the current Blender content needs migration.

        Note that return value is checked based on actual content,
        irrespective of the current plugin version."""
        return any(
            _get_legacy_integer_preset_id(effect) is not None
            for effect in _iter_light_effects()
        )

    def execute(self, context: Context, *, log: Logger):
        """Executes the migration on the current Blender content."""
        converted = 0
        for effect in _iter_light_effects():
            legacy_value = _get_legacy_integer_preset_id(effect)
            if legacy_value is None:
                continue
            preset_id = get_preset_id_from_legacy_enum_value(legacy_value)
            try:
                migrated = migrate_legacy_preset_id(effect)
            except Exception:
                log.error(
                    f"Failed to convert the legacy preset with index {legacy_value} "
                    f"to {preset_id!r} in light effect {effect.name!r}",
                    exc_info=True,
                )
            else:
                if migrated:
                    converted += 1
                    log.info(
                        f"Converted the legacy preset with index {legacy_value} "
                        f"to {preset_id!r} in light effect {effect.name!r}."
                    )
        if converted:
            log.info(f"Converted the legacy presets of {converted} light effects.")

        return {"FINISHED"}
