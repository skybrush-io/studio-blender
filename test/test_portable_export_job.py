"""Run on each real OS; platform emulation is not acceptance evidence."""

import json
import sys

import pytest
from sbstudio.atomic_file import atomic_write_bytes
from sbstudio.background_job import BackgroundExportJob


def test_real_worker_handles_spaces_unicode_and_nested_output(tmp_path):
    target = tmp_path / "shows with spaces" / "द्रोण तारा – café.skyc"
    job = BackgroundExportJob(target)
    directory = job.directory
    try:
        # Use separate argv elements, never shell quoting. The same path must
        # round-trip through Windows CreateProcess and POSIX exec.
        code = (
            "import pathlib,sys; "
            "pathlib.Path(sys.argv[1]).write_bytes(b'validated artifact'); "
            "pathlib.Path(sys.argv[2]).write_text('{\"success\": true}')"
        )
        job.start(
            [
                sys.executable,
                "-c",
                code,
                str(job.artifact),
                str(directory / "result.json"),
            ]
        )
        assert job.process is not None
        assert job.process.wait(timeout=15) == 0
        assert not target.exists()
        assert job.commit() == []
        assert target.read_bytes() == b"validated artifact"
    finally:
        job.close()
    assert not directory.exists()


def test_real_worker_crash_preserves_previous_export(tmp_path):
    target = tmp_path / "show.skyc"
    target.write_bytes(b"previous export")
    job = BackgroundExportJob(target)
    try:
        job.start([sys.executable, "-c", "raise SystemExit(7)"])
        assert job.process is not None
        assert job.process.wait(timeout=15) == 7
        with pytest.raises(RuntimeError, match="did not finish"):
            job.commit()
        assert "destination unchanged" in job.error_message()
        assert target.read_bytes() == b"previous export"
    finally:
        job.close()


def test_close_stops_owned_worker_and_is_idempotent(tmp_path):
    job = BackgroundExportJob(tmp_path / "cancelled.skyc")
    directory = job.directory
    try:
        job.start([sys.executable, "-c", "import time; time.sleep(60)"])
        worker = job.process
        assert worker is not None
    finally:
        job.close()
    job.close()
    assert worker.poll() is not None
    assert not directory.exists()
    assert not job.destination.exists()


@pytest.mark.parametrize("result", [None, "not json", json.dumps({"success": False})])
def test_missing_or_invalid_worker_result_never_commits(tmp_path, result):
    job = BackgroundExportJob(tmp_path / "show.skyc")
    job.destination.write_bytes(b"previous export")
    try:
        job.artifact.write_bytes(b"incomplete")
        if result is not None:
            (job.directory / "result.json").write_text(result)
        job.start([sys.executable, "-c", "pass"])
        assert job.process is not None
        assert job.process.wait(timeout=15) == 0
        with pytest.raises((OSError, ValueError, RuntimeError)):
            job.commit()
        assert job.destination.read_bytes() == b"previous export"
    finally:
        job.close()


def test_destination_directory_is_not_replaced(tmp_path):
    target = tmp_path / "directory.skyc"
    target.mkdir()
    child = target / "keep.txt"
    child.write_bytes(b"keep")
    with pytest.raises(OSError):
        atomic_write_bytes(target, b"new show")
    assert child.read_bytes() == b"keep"
    assert list(tmp_path.iterdir()) == [target]


def test_cancellation_escalates_after_grace_period(tmp_path, monkeypatch):
    class StubbornWorker:
        terminated = False
        killed = False

        def poll(self):
            return -9 if self.killed else None

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

    clock = [10.0]
    monkeypatch.setattr("sbstudio.background_job.monotonic", lambda: clock[0])
    job = BackgroundExportJob(tmp_path / "show.skyc")
    worker = StubbornWorker()
    job.process = worker
    try:
        job.cancel()
        assert worker.terminated
        assert job.poll() is None and not worker.killed
        clock[0] += 2.1
        job.poll()
        assert worker.killed
        assert job.poll() == -9
        assert not job.destination.exists()
    finally:
        job.close()
