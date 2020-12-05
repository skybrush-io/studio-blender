from typing import Optional

from .decorators import with_screen

__all__ = ("find_one_3d_view", "find_one_3d_view_and_its_area")


@with_screen
def find_one_3d_view(screen: Optional[str] = None):
    """Finds a 3D view in the Blender screen with the given name, and returns
    the view itself.

    Parameters:
        screen: the name of the Blender screen to scan; `None` means to use the
            current screen

    Returns:
        Optional[SpaceView3D]: the first 3D view that we find in the given
            Blender screen, or ``None`` if no 3D view was found
    """
    return find_one_3d_view_and_its_area(screen)[0]


@with_screen
def find_one_3d_view_and_its_area(screen: Optional[str] = None):
    """Finds a 3D view in the Blender screen with the given name, and returns
    the view and its containing area in a tuple.

    Parameters:
        screen: the name of the Blender screen to scan; `None` means to use the
            current screen

    Returns:
        (Optional[SpaceView3D], Optional[Area]): the first 3D view that we find
            in the given Blender screen and its area, or ``(None, None)`` if
            no 3D view was found
    """
    for area in screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    return space, area
    return None, None
