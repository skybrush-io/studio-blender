"""Helper functions that can be used in most of our Blender addons."""

from contextlib import contextmanager
from typing import ContextManager, Set, Type

import bpy
import re


def _get_menu_by_name(menu):
    menu = re.sub(r"[^A-Za-z]+", "_", menu.lower())
    if hasattr(bpy.types, "TOPBAR_MT_" + menu):
        return getattr(bpy.types, "TOPBAR_MT_" + menu)
    else:
        return getattr(bpy.types, "INFO_MT_" + menu)


_already_processed_with_make_annotations: Set[Type] = set()


def _make_annotations(cls):
    """Converts class fields to annotations.

    This is needed because apparently the syntax that Blender 2.80 uses for
    the class properties (i.e. using IntProperty(), FloatProperty() etc) confuses
    Python static type checkers like Pyright or Pylance. We stick to the older
    Blender 2.7x-style annotations and then convert them on-the fly when the
    class is registered as an operator.
    """
    # Before Blender 2.93, properties in Blender classes were instances of
    # tuples so we look for that. Blender 2.93 changed this to
    # bpy.props._PropertyDeferred
    try:
        from bpy.props import _PropertyDeferred as PropertyType
    except ImportError:
        PropertyType = tuple

    classes = list(reversed(cls.__mro__))
    bl_props = {}
    while classes:
        current_class = classes.pop()
        if (
            current_class != cls
            and current_class not in _already_processed_with_make_annotations
        ):
            _make_annotations(current_class)

    _already_processed_with_make_annotations.add(cls)
    bl_props.update(
        {k: v for k, v in cls.__dict__.items() if isinstance(v, PropertyType)}
    )

    if bl_props:
        if "__annotations__" not in cls.__dict__:
            cls.__annotations__ = {}
        annotations = cls.__dict__["__annotations__"]
        for k, v in bl_props.items():
            annotations[k] = v
            delattr(cls, k)

    return cls


def register_in_menu(menu, func):
    _get_menu_by_name(menu).append(func)


def register_header(cls):
    """Registers the given Blender header."""
    _make_annotations(cls)
    bpy.utils.register_class(cls)


def register_list(cls):
    """Registers the given Blender list widget type."""
    _make_annotations(cls)
    bpy.utils.register_class(cls)


def register_menu(cls):
    """Registers the given Blender menu type."""
    _make_annotations(cls)
    bpy.utils.register_class(cls)


def register_operator(cls):
    """Registers the given Blender operator."""
    _make_annotations(cls)
    bpy.utils.register_class(cls)


def register_panel(cls):
    """Registers the given Blender panel."""
    _make_annotations(cls)
    bpy.utils.register_class(cls)


def register_translations(translations_dict):
    """Registers the given translations dictionary."""
    bpy.app.translations.register(__name__, translations_dict)


def register_type(cls):
    """Registers the given Blender custom type."""
    _make_annotations(cls)
    bpy.utils.register_class(cls)


def unregister_from_menu(menu, func):
    _get_menu_by_name(menu).remove(func)


def unregister_header(cls):
    """Unregisters the given Blender header."""
    bpy.utils.unregister_class(cls)


def unregister_list(cls):
    """Unregisters the given Blender list widget type."""
    bpy.utils.unregister_class(cls)


def unregister_menu(cls):
    """Unregisters the given Blender menu."""
    bpy.utils.unregister_class(cls)


def unregister_operator(cls):
    """Unregisters the given Blender operator."""
    bpy.utils.unregister_class(cls)


def unregister_panel(cls):
    """Unregisters the given Blender panel."""
    bpy.utils.unregister_class(cls)


def unregister_translations():
    """Unregisters the given translations dictionary."""
    bpy.app.translations.unregister(__name__)


def unregister_type(cls):
    """Unregisters the given Blender custom type."""
    bpy.utils.unregister_class(cls)


def enter_edit_mode(obj=None, *, context=None):
    """Enters edit mode in the current context."""
    if obj is not None:
        context = context or bpy.context
        context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT", toggle=False)


def is_online_access_allowed() -> bool:
    """Returns whether the settings of the user allow add-ons to access online
    resources.
    """
    # bpy.app.online_access was added in Blender 4.2; earlier versions default
    # to True
    return bool(getattr(bpy.app, "online_access", True))


@contextmanager
def temporarily_exit_edit_mode(context=None) -> ContextManager[None]:
    """Context manager that temporarily exits edit mode if the context is in
    edit mode, and restores it upon exiting the context.

    The context manager is a no-op if Blender is not in edit mode.
    """
    context = context or bpy.context
    mode = context.mode
    if mode != "EDIT_MESH":
        yield
    else:
        ob = context.view_layer.objects.active
        with use_mode_for_object("OBJECT"):
            yield
        enter_edit_mode(ob, context=context)


@contextmanager
def use_menu(menu, func):
    """Context manager that registers the given function in a Blender menu when
    entering the context and unregisters it when exiting the context.
    """
    register_in_menu(menu, func)
    try:
        yield
    finally:
        unregister_from_menu(menu, func)


@contextmanager
def use_mode_for_object(mode) -> ContextManager[str]:
    """Context manager that temporarily switches the mode of the active object
    to a new one and then switches the object back to the original mode when
    exiting the context.

    Yields:
        the original mode that was active _before_ entering the given mode
    """
    original_mode = bpy.context.object.mode
    if original_mode == mode:
        yield original_mode
    else:
        context = bpy.context.copy()
        bpy.ops.object.mode_set(context, mode=mode)
        try:
            yield original_mode
        finally:
            # Make sure that we switch the mode back for the _original_ object;
            # that's why we've made a copy. This allows the user to change the
            # selection in the context without messing up what we do here.
            bpy.ops.object.mode_set(context, mode=original_mode)


@contextmanager
def use_operator(cls):
    """Context manager that registers the given Blender operator when entering
    the context and unregisters it when exiting the context.
    """
    register_operator(cls)
    try:
        yield
    finally:
        unregister_operator(cls)
