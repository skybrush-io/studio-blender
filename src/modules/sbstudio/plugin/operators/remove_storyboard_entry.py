from .base import StoryboardOperator

__all__ = ("RemoveStoryboardEntryOperator",)


class RemoveStoryboardEntryOperator(StoryboardOperator):
    """Blender operator that removes the selected storyboard entry."""

    bl_idname = "skybrush.remove_storyboard_entry"
    bl_label = "Remove Selected Storyboard Entry"
    bl_description = "Remove the selected entry from the storyboard"

    def execute_on_storyboard(self, storyboard, context):
        storyboard.remove_active_entry()
        return {"FINISHED"}
