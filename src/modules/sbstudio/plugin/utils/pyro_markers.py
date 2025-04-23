from bpy.types import Object

from sbstudio.model.pyro_markers import PyroMarker, PyroMarkers


__all__ = (
    "add_pyro_marker_to_object",
    "get_pyro_markers_of_object",
    "set_pyro_markers_of_object",
)


def add_pyro_marker_to_object(ob: Object, channel: int, marker: PyroMarker) -> None:
    """Add a pyro marker to the Skybrush context of an object.

    Args:
        object: the object to add the new pyro marker to
        channel: the pyro channel to add the trigger event to
        marker: the marker to add
    """
    markers = get_pyro_markers_of_object(ob)
    markers.markers[int(channel)] = marker
    set_pyro_markers_of_object(ob, markers)


def get_pyro_markers_of_object(ob: Object) -> PyroMarkers:
    """Get pyro markers from the Skybrush context of an object.

    Args:
        object: the object to get pyro markers from

    Returns:
        pyro markers
    """
    return PyroMarkers.from_str(ob.skybrush.pyro_markers)


def set_pyro_markers_of_object(ob: Object, markers: PyroMarkers) -> None:
    """Set pyro markers of an object in its Skybrush context.

    Args:
        object: the object to set pyro markers of
        markers: the markers to set
    """
    ob.skybrush.pyro_markers = markers.as_str()
