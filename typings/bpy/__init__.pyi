from collections.abc import Sequence

import bpy.app as app
import bpy.ops as ops
import bpy.path as path
import bpy.utils as utils

from .types import BlendData, Context, Object

__all__ = ("app", "context", "data", "ops", "path", "utils")

class _Context(Context):
    selected_objects: Sequence[Object]

context: _Context
data: BlendData
