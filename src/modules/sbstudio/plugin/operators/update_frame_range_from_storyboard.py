from .base import StoryboardOperator

__all__ = ("UpdateFrameRangeFromStoryboardOperator",)


class UpdateFrameRangeFromStoryboardOperator(StoryboardOperator):
    """Blender operator that updates the render frame range according to the storyboard."""

    bl_idname = "skybrush.update_frame_range_from_storyboard"
    bl_label = "Update Frame Range from Storyboard"
    bl_description = "Updates the frame range to be synchronized with the storyboard"

    def execute_on_storyboard(self, storyboard, context):
        frame_start = min(storyboard.frame_start, 0)
        frame_end = storyboard.frame_end

        if context.scene.use_preview_range:
            context.scene.frame_preview_start = frame_start
            context.scene.frame_preview_end = frame_end
        else:
            context.scene.frame_start = frame_start
            context.scene.frame_end = frame_end

        return {"FINISHED"}
