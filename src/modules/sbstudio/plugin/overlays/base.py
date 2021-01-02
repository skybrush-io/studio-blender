"""Base class for overlays that can register drawing callbacks on the
Blender 3D view and that can be enabled or disabled on-demand.
"""

from abc import ABCMeta
from bpy.types import SpaceView3D

__all__ = ("Overlay",)


class Overlay(metaclass=ABCMeta):
    """Base class for overlays that can register drawing callbacks on the
    Blender 3D view and that can be enabled or disabled on-demand.

    Add a `draw_3d()` method in derived classes to draw in 3D space.
    Add a `draw_2d()` method in derived classes to draw in 2D space; this is
    useful for text overlays.
    """

    def __init__(self):
        """Constructor."""
        self._enabled = False
        self._handler_2d = None
        self._handler_3d = None

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        value = bool(value)

        if self._enabled == value:
            return

        if self._enabled:
            if self._handler_2d:
                SpaceView3D.draw_handler_remove(self._handler_2d, "WINDOW")
                self._handler_2d = None
            if self._handler_3d:
                SpaceView3D.draw_handler_remove(self._handler_3d, "WINDOW")
                self._handler_3d = None
            self.dispose()

        self._enabled = value

        if self._enabled:
            self.prepare()
            if hasattr(self, "draw_3d"):
                self._handler_3d = SpaceView3D.draw_handler_add(
                    self.draw_3d, (), "WINDOW", getattr(self, "event", "POST_VIEW")
                )
            if hasattr(self, "draw_2d"):
                self._handler_2d = SpaceView3D.draw_handler_add(
                    self.draw_2d, (), "WINDOW", getattr(self, "event", "POST_PIXEL")
                )

    def prepare(self) -> None:
        """Callback that is called _once_ before the overlay has been enabled.
        This is the place to prepare shaders and batches by assingning them
        to properties of the class instance.
        """
        pass

    def dispose(self) -> None:
        """Callback that is called _once_ after the overlay has been disabled.
        This is the place to undo all the preparations done in `prepare()` and
        release references to shaders, batches and vertex buffers.
        """
        pass
