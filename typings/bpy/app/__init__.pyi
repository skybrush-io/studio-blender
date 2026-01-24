import bpy.app.handlers as handlers

__all__ = (
    "handlers",
    "online_access",
    "online_access_override",
    "version",
    "version_file",
    "version_string",
)

version: tuple[int, int, int]
version_file: tuple[int, int, int]
version_string: str

online_access: bool
online_access_override: bool
