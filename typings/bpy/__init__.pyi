from typing import Tuple

from .types import BlendData, Context

class _App:
    version: Tuple[int, int, int]
    version_file: Tuple[int, int, int]
    version_string: str

app: _App
context: Context
data: BlendData
