from bpy.types import Context, Operator

from sbstudio.plugin.migrations import (
    get_migration_details,
    is_migration_needed,
    migrate,
)

__all__ = ("RunAllMigrationOperators",)


CONFIRMATION = """
The format of this file needs to be updated to work correctly with
the current version of the Skybrush add-on.

The file will be updated from version {current} to {latest}.

Do you want to proceed?
"""


class RunAllMigrationOperators(Operator):
    """Runs all migration operators on the current scene to ensure that the format of
    all its internal objects are up-to-date.
    """

    bl_idname = "skybrush.run_all_migrations"
    bl_label = "Update to Latest File Format"
    bl_description = "Updates the format of the current file to the latest version"

    @classmethod
    def poll(self, context: Context) -> bool:
        return is_migration_needed(context)

    def invoke(self, context: Context, event):
        if is_migration_needed(context, strict=True):
            # Some migrations will actually change content, so we ask for confirmation
            _, current, latest = get_migration_details(context)
            return context.window_manager.invoke_confirm(
                self,
                event,
                title=self.bl_label,
                message=CONFIRMATION.format(current=current, latest=latest),
            )
        else:
            # We know that no migrations need to be run based on actual content, so we
            # just run them without confirmation (we know that we are only going to
            # bump the version number)
            return self.execute(context)

    def execute(self, context: Context):
        migrate(context)
        return {"FINISHED"}
