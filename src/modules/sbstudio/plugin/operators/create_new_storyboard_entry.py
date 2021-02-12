from .base import StoryboardOperator

__all__ = ("CreateNewStoryboardEntryOperator",)


class CreateNewStoryboardEntryOperator(StoryboardOperator):
    """Blender operator that creates a new, empty storyboard entry."""

    bl_idname = "skybrush.create_new_storyboard_entry"
    bl_label = "Create New Storyboard Entry"
    bl_description = "Creates a new storyboard entry at the end of the storyboard."

    def execute_on_storyboard(self, storyboard, context):
        storyboard.add_new_entry(name="Untitled", select=True)
        return {"FINISHED"}
