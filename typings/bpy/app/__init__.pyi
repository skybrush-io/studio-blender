import bpy.app.handlers as handlers
import bpy.app.timers as timers
import bpy.app.translations as translations

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
