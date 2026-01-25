import logging
from typing import Type

from bpy.types import Context

from .base import Migration
from .use_common_material_for_all_drones import UseSharedMaterialForAllDronesMigration

__all__ = ("get_migration_details", "is_migration_needed", "migrate")

migrations: dict[int, Type[Migration]] = {}
candidates: list[Type[Migration]] = [
    UseSharedMaterialForAllDronesMigration  # version 1 -> 2
]
LATEST_VERSION: int = 1

log = logging.getLogger(__name__)


for migration in candidates:
    version_from, version_to = migration.version_range
    if version_from >= version_to:
        raise RuntimeError(
            f"Invalid migration from version {version_from} to {version_to}"
        )

    existing_migration = migrations.get(version_from)
    if existing_migration is not None:
        _, existing_version_to = existing_migration.version_range
        if existing_version_to > version_to:
            # Existing migration is better as it migrates to a higher version
            continue
        elif existing_version_to == version_to:
            raise ValueError(
                f"Multiple migrations found from version {version_from} to {version_to}: "
                f"{existing_migration} and {migration}"
            )

    migrations[version_from] = migration
    LATEST_VERSION = max(LATEST_VERSION, version_to)


def get_migration_details(context: Context) -> tuple[bool, int, int]:
    """Returns a tuple indicating whether migration is needed, the current version,
    and the latest version that we can migrate to.
    """
    global LATEST_VERSION

    skybrush = context.scene.skybrush
    if skybrush:
        current_version = skybrush.version
        return current_version < LATEST_VERSION, current_version, LATEST_VERSION
    else:
        return False, 0, LATEST_VERSION


def is_migration_needed(context: Context, *, strict: bool = False) -> bool:
    """Returns whether any migration is needed for the current Blender content.

    Args:
        context: the current Blender context
        strict: whether to perform strict checking based on actual content.
            If False, only the version number is checked.
    """
    global LATEST_VERSION

    skybrush = context.scene.skybrush
    if skybrush is None:
        return False

    if skybrush.version < LATEST_VERSION:
        return not strict or _is_migration_needed_strict(context)
    else:
        return False


def _is_migration_needed_strict(context: Context) -> bool:
    global LATEST_VERSION

    skybrush = context.scene.skybrush
    version = skybrush.version
    while version < LATEST_VERSION:
        migration = migrations.get(version)
        if migration is None:
            # No migration found for this version. This is an error, but we want the
            # user to see it so we return that migration is needed.
            return True

        current_version, next_version = migration.version_range
        assert current_version < next_version

        if migration.needs_migration(context):
            return True

        version = next_version

    return False


def migrate(context: Context, *, dry_run: bool = False) -> None:
    """Runs all needed migrations on the current Blender content.

    Args:
        context: the current Blender context
        dry_run: if True, no actual migration will be performed,
            but the function will still check which migrations
            would be needed.
    """
    if not is_migration_needed(context):
        return

    skybrush = context.scene.skybrush
    while skybrush.version < LATEST_VERSION:
        migration = migrations.get(skybrush.version)
        if migration is None:
            raise RuntimeError(f"No migration found from version {skybrush.version}")

        current_version, next_version = migration.version_range
        assert current_version < next_version

        log.info(f"Updating from version {current_version} to {next_version}")

        if migration.needs_migration(context):
            migration_instance = migration()
            migration_instance.execute(context, log=log)

        skybrush.version = next_version

    log.info(f"Successfully migrated to {skybrush.version}")
