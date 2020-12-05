"""Helper functions that can be used in most of our Blender addons."""

from contextlib import contextmanager

import bpy
import re


def _get_menu_by_name(menu):
    menu = re.sub(r"[^A-Za-z]+", "_", menu.lower())
    if hasattr(bpy.types, "TOPBAR_MT_" + menu):
        return getattr(bpy.types, "TOPBAR_MT_" + menu)
    else:
        return getattr(bpy.types, "INFO_MT_" + menu)


def _make_annotations(cls):
    """Converts class fields to annotations.

    This is needed because apparently the syntax that Blender 2.80 uses for
    the class properties (i.e. using IntProperty(), FloatProperty() etc) is
    barfed upon by the linter. We stick to the older Blender 2.7x-style
    annotation and then convert it on-the fly when the class is registered
    as an operator.
    """
    bl_props = {k: v for k, v in cls.__dict__.items() if isinstance(v, tuple)}

    if bl_props:
        if "__annotations__" not in cls.__dict__:
            setattr(cls, "__annotations__", {})
        annotations = cls.__dict__["__annotations__"]
        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)

    return cls


def register_in_menu(menu, func):
    _get_menu_by_name(menu).append(func)


def register_operator(cls):
    """Registers the given Blender operator."""
    _make_annotations(cls)
    bpy.utils.register_class(cls)


def unregister_from_menu(menu, func):
    _get_menu_by_name(menu).remove(func)


def unregister_operator(cls):
    """Unregisters the given Blender operator."""
    bpy.utils.unregister_class(cls)


@contextmanager
def with_menu(menu, func):
    """Context manager that registers the given function in a Blender menu when
    entering the context and unregisters it when exiting the context.
    """
    register_in_menu(menu, func)
    try:
        yield
    finally:
        unregister_from_menu(menu, func)


@contextmanager
def with_operator(cls):
    """Context manager that registers the given Blender operator when entering
    the context and unregisters it when exiting the context.
    """
    register_operator(cls)
    try:
        yield
    finally:
        unregister_operator(cls)
