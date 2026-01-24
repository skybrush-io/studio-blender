from collections.abc import Sequence

import bpy.app as app

from .types import BlendData, Context, Object

__all__ = ("app", "context", "data")

class _Context(Context):
    selected_objects: Sequence[Object]

context: _Context
data: BlendData
