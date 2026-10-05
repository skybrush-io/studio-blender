"""Commit an export only after its complete contents have been flushed."""

import os
from pathlib import Path
from stat import S_IMODE
from uuid import uuid4


def atomic_write_bytes(destination: str | Path, data: bytes) -> None:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = S_IMODE(destination.stat().st_mode)
    except FileNotFoundError:
        mode = None
    temporary = None
    try:
        candidate = destination.with_name(f".{destination.name}.{uuid4().hex}")
        # Let the OS apply the umask for new files, without temporarily changing
        # the process-wide umask (which would race with other threads).
        fd = os.open(
            candidate,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o666,
        )
        temporary = candidate
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            if mode is not None:
                os.chmod(temporary, mode)
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
