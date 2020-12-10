from .base import StoryboardOperator

from sbstudio.plugin.constants import (
    DEFAULT_STORYBOARD_ENTRY_DURATION,
    DEFAULT_STORYBOARD_TRANSITION_DURATION,
)

__all__ = ("CreateNewStoryboardEntryOperator",)


class CreateNewStoryboardEntryOperator(StoryboardOperator):
    """Blender operator that creates a new, empty storyboard entry."""

    bl_idname = "skybrush.create_new_storyboard_entry"
    bl_label = "Create New Storyboard Entry"
    bl_description = "Creates a new storyboard entry at the end of the storyboard."

    def execute_on_storyboard(self, storyboard, context):
        entry = storyboard.entries.add()
        entry.frame_start = (
            storyboard.frame_end
            + context.scene.render.fps * DEFAULT_STORYBOARD_TRANSITION_DURATION
            if storyboard.entries
            else context.scene.frame_start
        )
        entry.duration = context.scene.render.fps * DEFAULT_STORYBOARD_ENTRY_DURATION
        entry.name = "Untitled"

        storyboard.active_entry_index = len(storyboard.entries) - 1
        return {"FINISHED"}
