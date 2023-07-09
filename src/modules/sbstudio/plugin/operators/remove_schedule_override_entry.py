from .base import StoryboardEntryOperator

__all__ = ("RemoveScheduleOverrideEntryOperator",)


class RemoveScheduleOverrideEntryOperator(StoryboardEntryOperator):
    """Blender operator that removes the selected schedule override entry
    from the current storyboard entry."""

    bl_idname = "skybrush.remove_schedule_override_entry"
    bl_label = "Remove Selected Schedule Override Entry"
    bl_description = (
        "Remove the selected schedule override entry from the selected "
        "storyboard entry"
    )

    @classmethod
    def poll(cls, context):
        if not StoryboardEntryOperator.poll(context):
            return False

        entry = context.scene.skybrush.storyboard.active_entry
        return entry.active_schedule_override_entry is not None

    def execute_on_storyboard_entry(self, entry, context):
        entry.remove_active_schedule_override_entry()
        return {"FINISHED"}
