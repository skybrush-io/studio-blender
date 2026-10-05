import os
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest
from sbstudio.atomic_file import atomic_write_bytes
from sbstudio.math.motion_diagnostics import normalize_phases
from sbstudio.timing import effective_fps, export_segments


def test_fractional_frame_rate():
    fps = effective_fps(SimpleNamespace(fps=24, fps_base=1.001))
    assert 240 / fps == pytest.approx(10.01)
    assert (264 / fps - 24 / fps) == pytest.approx(10.01)


def test_phase_clipping_and_origin():
    assert export_segments(
        {"takeoff": (0, 1), "show": (1, 30), "landing": (30, 40)}, 10, 35
    ) == {"show": (0, 20), "landing": (20, 25)}


def test_phase_clipping_preserves_invalid_interval():
    assert export_segments({"takeoff": (5, 3)}, 0, 10) == {"takeoff": (5, 3)}


@pytest.mark.parametrize("base", [0, -1, float("nan"), float("inf")])
def test_invalid_frame_rate(base):
    with pytest.raises(ValueError):
        effective_fps(SimpleNamespace(fps=24, fps_base=base))


def test_atomic_replace(tmp_path):
    target = tmp_path / "show.skyc"
    target.write_bytes(b"old")
    atomic_write_bytes(target, b"new")
    assert target.read_bytes() == b"new"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("operation", ["chmod", "fsync", "replace"])
def test_failed_commit_preserves_original(tmp_path, monkeypatch, operation):
    target = tmp_path / "show.skyc"
    target.write_bytes(b"old")

    def fail(*args):
        raise OSError("simulated storage failure")

    monkeypatch.setattr(f"sbstudio.atomic_file.os.{operation}", fail)
    with pytest.raises(OSError):
        atomic_write_bytes(target, b"new")
    assert target.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
@pytest.mark.parametrize("mode", [0o600, 0o640, 0o664])
def test_atomic_replace_preserves_existing_mode(tmp_path, mode):
    target = tmp_path / "show.skyc"
    target.write_bytes(b"old")
    target.chmod(mode)
    atomic_write_bytes(target, b"new")
    assert target.read_bytes() == b"new"
    assert stat.S_IMODE(target.stat().st_mode) == mode


@pytest.mark.skipif(os.name == "nt", reason="POSIX umask")
@pytest.mark.parametrize("mask", [0o022, 0o027, 0o077])
def test_new_atomic_file_uses_umask(tmp_path, mask):
    target = tmp_path / "new.skyc"
    # Change umask only in a subprocess, never in the test runner/Blender.
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,sys; from sbstudio.atomic_file import atomic_write_bytes; "
            "os.umask(int(sys.argv[2])); atomic_write_bytes(sys.argv[1], b'new')",
            str(target),
            str(mask),
        ],
        check=True,
    )
    assert stat.S_IMODE(target.stat().st_mode) == 0o666 & ~mask


def test_exclusive_temporary_creation_never_removes_another_file(tmp_path, monkeypatch):
    target = tmp_path / "show.skyc"
    candidate = tmp_path / ".show.skyc.collision"
    candidate.write_bytes(b"another writer")
    monkeypatch.setattr(
        "sbstudio.atomic_file.uuid4", lambda: SimpleNamespace(hex="collision")
    )
    with pytest.raises(FileExistsError):
        atomic_write_bytes(target, b"new")
    assert candidate.read_bytes() == b"another writer"
    assert not target.exists()


def test_empty_phase_does_not_discard_valid_show():
    phases, issues = normalize_phases({"takeoff": (0, 0), "show": (0, 10)})
    assert phases == [(0, 10, "show")]
    assert issues == ["empty interval omitted: takeoff"]


@pytest.mark.parametrize(
    "interval", [None, (1,), (2, 1), (0, "bad"), (0, float("nan"))]
)
def test_invalid_phase_fails_closed(interval):
    phases, issues = normalize_phases({"takeoff": interval, "show": (0, 10)})
    assert not phases
    assert issues
