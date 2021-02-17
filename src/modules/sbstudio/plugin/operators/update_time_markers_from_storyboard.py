from .base import StoryboardOperator

__all__ = ("UpdateTimeMarkersFromStoryboardOperator",)


class UpdateTimeMarkersFromStoryboardOperator(StoryboardOperator):
    """Blender operator that updates time markers according to the storyboard."""

    bl_idname = "skybrush.update_time_markers_from_storyboard"
    bl_label = "Update Time Markers from Storyboard"
    bl_description = "Update all time markers to be synchronized with the storyboard"

    def execute_on_storyboard(self, storyboard, context):
        markers = context.scene.timeline_markers
        markers.clear()
        for entry in storyboard.entries:
            markers.new("at {}".format(entry.name), frame=entry.frame_start)
            if entry.duration > 0:
                markers.new(
                    "{} ends".format(entry.name),
                    frame=entry.frame_start + entry.duration,
                )

        return {"FINISHED"}
