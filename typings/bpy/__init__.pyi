from typing import Sequence

from .types import BlendData, Context, Object

class _App:
    version: tuple[int, int, int]
    version_file: tuple[int, int, int]
    version_string: str

class _Context(Context):
    selected_objects: Sequence[Object]

app: _App
context: _Context
data: BlendData
