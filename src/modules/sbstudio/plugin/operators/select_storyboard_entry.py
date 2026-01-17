from __future__ import annotations

from typing import TYPE_CHECKING

from sbstudio.plugin.model.storyboard import Storyboard, get_storyboard

from .base import StoryboardOperator

if TYPE_CHECKING:
    from bpy.types import Context


__all__ = ("SelectStoryboardEntryForCurrentFrameOperator",)


class SelectStoryboardEntryForCurrentFrameOperator(StoryboardOperator):
    """Blender operator that selects the storyboard entry that contains the
    current frame.

    When the current frame falls between storyboard entries, selects the
    storyboard entry _after_ the current frame.
    """

    bl_idname = "skybrush.select_storyboard_entry_for_current_frame"
    bl_label = "Select Storyboard Entry for Current Frame"
    bl_description = (
        "Select the storyboard entry that contains the current frame. If the "
        "current frame falls between storyboard entries, selects the next entry. "
        "Clears the selection if the current frame is after the end of the "
        "storyboard."
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(
            StoryboardOperator.poll(context) and get_storyboard(context=context).entries
        )

    def execute_on_storyboard(self, storyboard: Storyboard, context: Context):
        frame = context.scene.frame_current
        index = storyboard.get_index_of_entry_containing_frame(frame)
        if index < 0:
            index = storyboard.get_index_of_entry_after_frame(frame)
        storyboard.active_entry_index = index
        return {"FINISHED"}
