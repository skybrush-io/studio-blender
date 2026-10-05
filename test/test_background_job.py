import json
import sys

import pytest
from sbstudio.background_job import BackgroundExportJob


class Completed:
    def poll(self):
        return 0


def complete(job, data=b"new", warnings=None):
    job.artifact.write_bytes(data)
    (job.directory / "result.json").write_text(
        json.dumps({"success": True, "warnings": warnings or []})
    )
    job.process = Completed()


def test_success_commits_and_cleans_snapshot(tmp_path):
    target = tmp_path / "show.skyc"
    target.write_bytes(b"old")
    job = BackgroundExportJob(target)
    directory = job.directory
    try:
        complete(job, warnings=["separation"])
        assert target.read_bytes() == b"old"
        assert job.commit() == ["separation"]
        assert target.read_bytes() == b"new"
    finally:
        job.close()
    assert not directory.exists()


@pytest.mark.parametrize("reason", ["cancelled", "changed", "empty", "failed"])
def test_uncommittable_job_preserves_destination(tmp_path, reason):
    target = tmp_path / "show.skyc"
    target.write_bytes(b"old")
    job = BackgroundExportJob(target)
    try:
        complete(job)
        if reason == "cancelled":
            job.cancel()
        elif reason == "changed":
            target.write_bytes(b"externally changed")
        elif reason == "empty":
            job.artifact.write_bytes(b"")
        else:
            (job.directory / "result.json").write_text('{"success":false}')
        with pytest.raises(RuntimeError):
            job.commit()
        assert target.read_bytes() == (
            b"externally changed" if reason == "changed" else b"old"
        )
    finally:
        job.close()


def test_cancellation_terminates_real_worker_and_removes_temporary_files(tmp_path):
    job = BackgroundExportJob(tmp_path / "show.skyc")
    directory = job.directory
    try:
        job.start([sys.executable, "-c", "import time; time.sleep(60)"])
        job.cancel()
        assert job.process is not None
        job.process.wait(timeout=5)
        with pytest.raises(RuntimeError, match="cancelled"):
            job.commit()
        assert not job.destination.exists()
    finally:
        job.close()
    assert not directory.exists()


def test_atomic_commit_failure_preserves_existing_file(tmp_path, monkeypatch):
    target = tmp_path / "show.skyc"
    target.write_bytes(b"old")
    job = BackgroundExportJob(target)
    try:
        complete(job)

        def fail(*args):
            raise OSError("simulated disk failure")

        monkeypatch.setattr("sbstudio.atomic_file.os.replace", fail)
        with pytest.raises(OSError):
            job.commit()
        assert target.read_bytes() == b"old"
    finally:
        job.close()
