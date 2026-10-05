"""Process-isolated export lifecycle; no Blender API calls or hardware access."""

import atexit
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from .atomic_file import atomic_write_bytes


def _fingerprint(path):
    try:
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns
    except FileNotFoundError:
        return None


class BackgroundExportJob:
    def __init__(self, destination):
        self.destination = Path(destination)
        self.original = _fingerprint(self.destination)
        self.temporary = TemporaryDirectory(prefix="skybrush-export-")
        self.directory = Path(self.temporary.name)
        self.artifact = self.directory / self.destination.name
        self.process = None
        self.cancelled_at = None
        self.log = None
        self.closed = False
        self.export_gate = None
        atexit.register(self.close)

    def start(self, command):
        self.log = (self.directory / "worker.log").open("wb")
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=self.log,
            stderr=subprocess.STDOUT,
            shell=False,
        )

    def cancel(self):
        if self.cancelled_at is None:
            self.cancelled_at = monotonic()
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()

    def poll(self):
        if self.process is None:
            raise RuntimeError("Export worker has not started")
        code = self.process.poll()
        if code is None and self.cancelled_at is not None:
            if monotonic() - self.cancelled_at > 2:
                self.process.kill()
        return code

    def commit(self):
        if self.cancelled_at is not None:
            raise RuntimeError("Export was cancelled; destination unchanged")
        if self.poll() != 0:
            raise RuntimeError("Export worker did not finish successfully")
        result = json.loads((self.directory / "result.json").read_text())
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Export worker failed"))
        data = self.artifact.read_bytes()
        if not data:
            raise RuntimeError("Export worker produced an empty file")
        if _fingerprint(self.destination) != self.original:
            raise RuntimeError(
                "Destination changed during export; refusing to overwrite it"
            )
        atomic_write_bytes(self.destination, data)
        self.export_gate = result.get("export_gate")
        return result.get("warnings", [])

    def error_message(self):
        result = self.directory / "result.json"
        if result.exists():
            try:
                return json.loads(result.read_text()).get(
                    "error", "Export worker failed"
                )
            except (OSError, ValueError):
                pass
        return "Export worker stopped unexpectedly; destination unchanged"

    def close(self):
        if self.closed:
            return
        if self.process is not None and self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=5)
        if self.log is not None:
            self.log.close()
        self.temporary.cleanup()
        self.closed = True
        atexit.unregister(self.close)
