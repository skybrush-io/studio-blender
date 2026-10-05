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


@pytest.mark.parametrize("operation", ["fsync", "replace"])
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
