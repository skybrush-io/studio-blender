from json import dumps, loads
from typing import List, Optional

from sbstudio.plugin.utils.collections import filter_collection

from .base import StoryboardOperator

__all__ = ("UpdateTimeMarkersFromStoryboardOperator",)


class UpdateTimeMarkersFromStoryboardOperator(StoryboardOperator):
    """Blender operator that updates time markers according to the storyboard."""

    bl_idname = "skybrush.update_time_markers_from_storyboard"
    bl_label = "Update Time Markers from Storyboard"
    bl_description = "Update all time markers to be synchronized with the storyboard"

    def execute_on_storyboard(self, storyboard, context):
        our_marker_names: Optional[List[str]] = None

        scene = context.scene

        markers = scene.timeline_markers
        our_marker_names_as_string = scene.skybrush.settings.time_markers
        if our_marker_names_as_string:
            try:
                our_marker_names = loads(our_marker_names_as_string)
            except Exception:
                # it's okay, our_marker_names remains at None
                pass

        if our_marker_names is not None:
            # Remove only those markers that we have created
            is_not_our_marker = lambda marker: marker.name not in our_marker_names
            filter_collection(markers, is_not_our_marker)
        else:
            markers.clear()

        our_marker_names = []
        for entry in storyboard.entries:
            marker_name = "at {}".format(entry.name)
            our_marker_names.append(marker_name)
            markers.new(marker_name, frame=entry.frame_start)

            if entry.duration > 0:
                marker_name = "{} ends".format(entry.name)
                our_marker_names.append(marker_name)
                markers.new(
                    marker_name,
                    frame=entry.frame_start + entry.duration,
                )

        try:
            scene.skybrush.settings.time_markers = dumps(our_marker_names)
        except Exception:
            # weird, but let's not fail
            pass

        return {"FINISHED"}
