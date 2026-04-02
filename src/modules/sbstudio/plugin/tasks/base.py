"""Base class for background tasks that get triggered in Blender in response
to certain events such as a frame change.
"""

import bpy
from bpy.app.handlers import persistent

__all__ = ("Task",)


_handler_names = [
    "depsgraph_update_pre",
    "depsgraph_update_post",
    "frame_change_pre",
    "frame_change_post",
    "load_factory_preferences_pre",
    "load_factory_preferences_post",
    "load_pre",
    "load_post",
    "redo_pre",
    "redo_post",
    "render_cancel",
    "render_complete",
    "render_init",
    "render_pre",
    "render_post",
    "render_stats",
    "render_write",
    "save_pre",
    "save_post",
    "undo_pre",
    "version_update",
]


class Task:
    """Base class for background tasks that get triggered in Blender in response
    to certain events such as a frame change.
    """

    functions = {}
    """Override this property in subclasses to define the handlers to register."""

    def register(cls):
        """Registers this task instance in Blender."""
        cls._registered_handlers = []

        for name in _handler_names:
            funcs = cls.functions.get(name)
            if not hasattr(funcs, "__iter__"):
                funcs = [funcs]

            for func in funcs:
                if callable(func):
                    func = persistent(func)
                    getattr(bpy.app.handlers, name).append(func)
                    cls._registered_handlers.append((name, func))

    def unregister(cls):
        """Unregisters this task instance from Blender."""
        for name, func in reversed(cls._registered_handlers):
            getattr(bpy.app.handlers, name).remove(func)

        del cls._registered_handlers
