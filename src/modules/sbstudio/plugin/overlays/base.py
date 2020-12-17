"""Base class for overlays that can register drawing callbacks on the
Blender 3D view and that can be enabled or disabled on-demand.
"""

from abc import ABCMeta
from bpy.types import SpaceView3D

__all__ = ("Overlay",)


class Overlay(metaclass=ABCMeta):
    """Base class for overlays that can register drawing callbacks on the
    Blender 3D view and that can be enabled or disabled on-demand.
    """

    def __init__(self):
        """Constructor."""
        self._enabled = False
        self._handler = None

    def draw(self):
        raise NotImplementedError

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        value = bool(value)

        if self._enabled == value:
            return

        if self._enabled:
            SpaceView3D.draw_handler_remove(self._handler, "WINDOW")
            self._handler = None
            self.dispose()

        self._enabled = value

        if self._enabled:
            self.prepare()
            self._handler = SpaceView3D.draw_handler_add(
                self.draw, (), "WINDOW", getattr(self, "event", "POST_VIEW")
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
