"""Base class for overlays that can register drawing callbacks on the
Blender 3D view and that can be enabled or disabled on-demand.
"""

from __future__ import annotations

from abc import ABCMeta
from collections.abc import Callable
from typing import ClassVar

import bpy
import gpu
from bpy.types import SpaceView3D

__all__ = ("Overlay",)


class Overlay(metaclass=ABCMeta):
    """Base class for overlays that can register drawing callbacks on the
    Blender 3D view and that can be enabled or disabled on-demand.

    Add a `draw_3d()` method in derived classes to draw in 3D space.
    Add a `draw_2d()` method in derived classes to draw in 2D space; this is
    useful for text overlays.
    """

    _enabled: bool
    """Whether the overlay is enabled."""

    _handler_2d: object
    """Handle to the registered Blender 2D draw handler, used when unregistering
    the overlay.
    """

    _handler_3d: object
    """Handle to the registered Blender 3D draw handler, used when unregistering
    the overlay.
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
                handler: Callable[[], None] = self.draw_3d  # type: ignore
                self._handler_3d = SpaceView3D.draw_handler_add(
                    handler, (), "WINDOW", getattr(self, "event", "POST_VIEW")
                )
            if hasattr(self, "draw_2d"):
                handler: Callable[[], None] = self.draw_2d  # type: ignore
                self._handler_2d = SpaceView3D.draw_handler_add(
                    handler, (), "WINDOW", getattr(self, "event", "POST_PIXEL")
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


class ShaderOverlay(Overlay):
    """Overlay subclass that works with a Blender built-in shader."""

    shader_type: ClassVar[str] = "UNIFORM_COLOR"

    _shader: gpu.types.GPUShader | None = None

    def __init__(self):
        super().__init__()

        self._shader = None

    def get_ui_scale(self) -> float:
        """Returns the scaling factor to use when drawing text at exact
        coordinates on the screen to cater for HiDPI vs non-HiDPI displays
        and the view scaling setting of the user.
        """
        # This value cannot be cached because the user might change the view
        # scaling settings in the preferences.
        return bpy.context.preferences.system.ui_scale

    def prepare(self) -> None:
        self._shader = gpu.shader.from_builtin(self.shader_type)

    def dispose(self) -> None:
        self._shader = None
