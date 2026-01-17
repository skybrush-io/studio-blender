from bpy.types import Context

from sbstudio.model.time_markers import TimeMarkers

__all__ = ("get_time_markers_from_context",)


def get_time_markers_from_context(context: Context) -> TimeMarkers:
    """Get time markers from the Skybrush or native Blender context.

    Args:
        context: the main Blender context

    Returns:
        time markers basically as a dictionary of (name, time) items in [s]

    """
    fps = context.scene.render.fps
    markers = context.scene.timeline_markers
    scene_settings = getattr(context.scene.skybrush, "settings", None)
    # if Skybrush markers are defined, use only those. If not, use all.
    our_marker_names_as_string = (
        scene_settings.time_markers
        if scene_settings and scene_settings.time_markers
        else [marker.name for marker in markers]
    )
    # create simple dictionary of markers
    our_markers = {
        marker.name: marker.frame / fps
        for marker in markers
        if marker.name in our_marker_names_as_string
    }

    return TimeMarkers(markers=our_markers)
