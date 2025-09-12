from .base import StoryboardEntryOperator

__all__ = (
    "SetStoryboardEntryEndFrameOperator",
    "SetStoryboardEntryStartFrameOperator",
)


class SetStoryboardEntryEndFrameOperator(StoryboardEntryOperator):
    """Blender operator that sets the end frame of the active storyboard entry
    to the current frame."""

    bl_idname = "skybrush.set_storyboard_entry_end_frame"
    bl_label = "Set Storyboard Entry End Frame"
    bl_description = "Sets the end frame of the storyboard entry to the current frame."

    def execute_on_storyboard_entry(self, entry, context):
        if entry is not None:
            entry.frame_end = context.scene.frame_current
        return {"FINISHED"}


class SetStoryboardEntryStartFrameOperator(StoryboardEntryOperator):
    """Blender operator that sets the start frame of the active storyboard entry
    to the current frame."""

    bl_idname = "skybrush.set_storyboard_entry_start_frame"
    bl_label = "Set Storyboard Entry Start Frame"
    bl_description = (
        "Sets the start frame of the storyboard entry to the current frame."
    )

    def execute_on_storyboard_entry(self, entry, context):
        if entry is not None:
            entry.frame_start = context.scene.frame_current
        return {"FINISHED"}
