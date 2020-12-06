from bpy.types import Context
from typing import Optional

from .utils import with_context

__all__ = ("deselect_all", "select_only")


@with_context
def deselect_all(*, context: Optional[Context] = None):
    """Deselects all objects in the given context (defaults to the current
    context).
    """
    for obj in context.selected_objects:
        obj.select_set(False)


def select_only(objects, *, context: Optional[Context] = None):
    """Selects only the given objects in the given context and deselects
    everything else (defaults to the current context).
    """
    deselect_all(context=context)
    for obj in objects:
        obj.select_set(True)
