from .base import StoryboardEntryOperator

__all__ = ("CreateNewScheduleOverrideEntryOperator",)


class CreateNewScheduleOverrideEntryOperator(StoryboardEntryOperator):
    """Blender operator that creates a new, empty schedule override in the
    currently selected storyboard entry."""

    bl_idname = "skybrush.create_new_schedule_override_entry"
    bl_label = "Create New Schedule Override"
    bl_description = (
        "Creates a new schedule override for the currently selected storyboard entry."
    )

    def execute_on_storyboard_entry(self, entry, context):
        entry.add_new_schedule_override()
        return {"FINISHED"}
