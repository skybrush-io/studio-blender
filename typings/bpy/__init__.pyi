from typing import Sequence

from .types import BlendData, Context, Object

class _App:
    version: tuple[int, int, int]
    version_file: tuple[int, int, int]
    version_string: str

    online_access: bool
    online_access_override: bool

class _Context(Context):
    selected_objects: Sequence[Object]

app: _App
context: _Context
data: BlendData
