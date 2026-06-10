from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

from bpy.types import Context

if TYPE_CHECKING:
    from bpy.types import Area, SpaceView3D

from .utils import with_screen

__all__ = (
    "find_all_3d_views",
    "find_all_3d_views_and_their_areas",
    "find_current_3d_view",
    "redraw_all_3d_views",
)


@with_screen
def find_all_3d_views(screen: str | None = None) -> Iterable[SpaceView3D]:
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
    screen: str | None = None,
) -> Iterable[tuple[SpaceView3D, Area]]:
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
    screen: str | None = None,
) -> Iterable[tuple[SpaceView3D, Area]]:
    for area in screen.areas:  # type: ignore
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    yield space, area


def find_current_3d_view(
    context: Context | None = None,
) -> SpaceView3D | None:
    """Finds the current 3D view in the given context, and returns
    the view itself.

    Parameters:
        context: the name of the Blender context to scan; `None` means to use the
            current context

    Returns:
        the current 3D view that we find in the given Blender context, or ``None``
        if no 3D view was found
    """
    if context is None:
        return None

    assert context is not None

    space = context.space_data
    if not space or space.type != "VIEW_3D":
        return None

    if TYPE_CHECKING:
        space = cast(SpaceView3D, space)

    return space


@with_screen
def redraw_all_3d_views(
    screen: str | None = None,
) -> None:
    """Redraws all 3D views in the Blender screen with the given name.

    Parameters:
        screen: the name of the Blender screen to redraw; `None` means to
            redraw the current screen

    """
    # Now that the decorator resolved the screen name, we can pass it on
    for _, area in _find_all_3d_views_and_their_areas(screen):
        area.tag_redraw()
