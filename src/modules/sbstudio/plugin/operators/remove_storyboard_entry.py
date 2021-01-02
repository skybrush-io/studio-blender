from .base import StoryboardOperator

__all__ = ("RemoveStoryboardEntryOperator",)


class RemoveStoryboardEntryOperator(StoryboardOperator):
    """Blender operator that removes the selected storyboard entry."""

    bl_idname = "skybrush.remove_storyboard_entry"
    bl_label = "Remove Selected Storyboard Entry"
    bl_description = "Remove the selected entry from the storyboard"

    @classmethod
    def poll(cls, context):
        return (
            StoryboardOperator.poll(context)
            and context.scene.skybrush.storyboard.active_entry is not None
        )

    def execute_on_storyboard(self, storyboard, context):
        storyboard.remove_active_entry()
        return {"FINISHED"}
