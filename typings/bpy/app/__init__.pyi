from collections.abc import Callable
from typing import Any

import bpy.app.handlers as handlers

__all__ = (
    "handlers",
    "online_access",
    "online_access_override",
    "tempdir",
    "timers",
    "translations",
    "version",
    "version_file",
    "version_string",
)

version: tuple[int, int, int]
version_file: tuple[int, int, int]
version_string: str

online_access: bool
online_access_override: bool

tempdir: str

class timers:
    def register(func: Callable[[], float | None]) -> None: ...
    def unregister(func: Callable[[], float | None]) -> None: ...

class translations:
    def register(cls: Any, data: dict[str, dict[str, str]]) -> None: ...
    def unregister(cls: Any, data: dict[str, dict[str, str]]) -> None: ...
