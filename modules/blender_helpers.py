"""Helper functions that can be used in most of our Blender addons."""

import bpy
import re

from pathlib import Path


def _get_menu_by_name(menu):
    menu = re.sub(r"[^A-Za-z]+", "_", menu.lower())
    if hasattr(bpy.types, "TOPBAR_MT_" + menu):
        return getattr(bpy.types, "TOPBAR_MT_" + menu)
    else:
        return getattr(bpy.types, "INFO_MT_" + menu)


def make_annotations(cls):
    """Converts class fields to annotations."""
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
    make_annotations(cls)
    bpy.utils.register_class(cls)


def unregister_from_menu(menu, func):
    _get_menu_by_name(menu).remove(func)


def unregister_operator(cls):
    """Unregisters the given Blender operator."""
    bpy.utils.unregister_class(cls)
