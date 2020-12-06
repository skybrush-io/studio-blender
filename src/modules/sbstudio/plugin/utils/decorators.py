import bpy

from functools import wraps

__all__ = ("with_context", "with_scene", "with_screen")


def with_context(func):
    """Decorator that can be applied to a function that takes a keyword
    argument named `context` and that fills the scene automatically from the
    current Blender context if it is `None` or not given.
    """

    @wraps(func)
    def wrapper(*args, **kwds):
        context = kwds.get("context")

        if context is None:
            kwds["context"] = bpy.context

        return func(*args, **kwds)

    return wrapper


def with_scene(func):
    """Decorator that can be applied to a function that takes a keyword
    argument named `scene` and that fills the scene automatically from the
    current Blender scene if it is `None` or not given.
    """

    @wraps(func)
    def wrapper(*args, **kwds):
        scene = kwds.get("scene")

        if scene is None:
            kwds["scene"] = bpy.context.scene

        if kwds["scene"] is None:
            raise ValueError("no scene given")

        return func(*args, **kwds)

    return wrapper


def with_screen(func):
    """Decorator that can be applied to a function that takes a keyword
    argument named `screen` and that fills the screen automatically from the
    current Blender screen if it is `None` or not given.
    """

    @wraps(func)
    def wrapper(*args, **kwds):
        screen = kwds.get("screen")

        if screen is None:
            kwds["screen"] = bpy.context.screen
        elif isinstance(screen, str):
            try:
                kwds["screen"] = bpy.data.screens[screen]
            except KeyError:
                kwds["screen"] = None

        if kwds["screen"] is None:
            raise ValueError("no screen given")

        return func(*args, **kwds)

    return wrapper
