from __future__ import annotations

from typing import Iterable, Optional, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from bpy.types import Area
    from bpy.types import SpaceView3D

from .utils import with_screen

__all__ = (
    "find_all_3d_views",
    "find_all_3d_views_and_their_areas",
    "find_one_3d_view",
    "find_one_3d_view_and_its_area",
)


@with_screen
def find_all_3d_views(screen: Optional[str] = None) -> Iterable[SpaceView3D]:
    """Finds all 3D views in the Blender screen with the given name, and returns
    an iterator that iterates over them.

    Parameters:
        screen: the name of the Blender screen to scan; `None` means to use the
            current screen

    Yields:
        the 3D views that we find in the given Blender screen
    """
    for space, _area in _find_all_3d_views_and_their_areas(screen):
        yield space


@with_screen
def find_all_3d_views_and_their_areas(
    screen: Optional[str] = None,
) -> Iterable[Tuple[SpaceView3D, Area]]:
    """Finds all 3D views in the Blender screen with the given name, and returns
    an iterator that iterates over them and their containing areas.

    Parameters:
        screen: the name of the Blender screen to scan; `None` means to use the
            current screen

    Yields:
        all 3D views that we find in the given Blender screen, and their
        corresponding areas, in tuples
    """
    # Now that the decorator resolved the screen name, we can pass it on
    return _find_all_3d_views_and_their_areas(screen)


def _find_all_3d_views_and_their_areas(
    screen: Optional[str] = None,
) -> Iterable[Tuple[SpaceView3D, Area]]:
    for area in screen.areas:  # type: ignore
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    yield space, area


@with_screen
def find_one_3d_view(screen: Optional[str] = None) -> Optional[SpaceView3D]:
    """Finds a 3D view in the Blender screen with the given name, and returns
    the view itself.

    Parameters:
        screen: the name of the Blender screen to scan; `None` means to use the
            current screen

    Returns:
        the first 3D view that we find in the given Blender screen, or ``None``
        if no 3D view was found
    """
    return find_one_3d_view_and_its_area(screen)[0]


@with_screen
def find_one_3d_view_and_its_area(
    screen: Optional[str] = None,
) -> Tuple[Optional[SpaceView3D], Optional[Area]]:
    """Finds a 3D view in the Blender screen with the given name, and returns
    the view and its containing area in a tuple.

    Parameters:
        screen: the name of the Blender screen to scan; `None` means to use the
            current screen

    Returns:
        the first 3D view that we find in the given Blender screen and its area,
        or ``(None, None)`` if no 3D view was found
    """
    for area in screen.areas:  # type: ignore
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    return space, area
    return None, None
