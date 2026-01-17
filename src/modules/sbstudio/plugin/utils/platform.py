from pathlib import Path

import bpy

#: Path object representing the temporary directory of the plugin within the
#: current Blender sessoin
_tmpdir = None


def get_temporary_directory() -> Path:
    """Returns a Path object representing the temporary directory of the plugin
    within the current Blender session.
    """
    global _tmpdir

    if _tmpdir is None:
        _tmpdir = Path(bpy.app.tempdir) / "skybrush"

    return _tmpdir


def open_file_with_default_application(path: str | Path) -> None:
    """Opens the given file with the default application of the OS."""
    path = str(path)

    try:
        from os import startfile

        startfile(path)
    except ImportError:
        import platform
        from subprocess import call

        if platform.system() == "Darwin":
            # macOS
            call(["open", path])
        else:
            # Most likely Linux
            call(["xdg-open", path])
