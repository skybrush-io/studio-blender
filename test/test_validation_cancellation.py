import pytest
from sbstudio.math.motion_audit import audit_sampled_motion
from sbstudio.math.trajectory_validation import validate_trajectories


class Cancelled(Exception):
    pass


def test_pairwise_validation_cancellation_propagates():
    calls = []

    def progress(done, total):
        calls.append((done, total))
        if done == 1:
            raise Cancelled

    paths = {str(i): [[0, i * 4, 0, 0], [1, i * 4, 0, 1]] for i in range(500)}
    with pytest.raises(Cancelled):
        validate_trajectories(paths, on_progress=progress)
    assert len(calls) == 2


def test_progress_completes_and_preserves_result():
    paths = {"A": [[0, 0, 0, 0], [1, 0, 0, 1]]}
    calls = []
    report = validate_trajectories(
        paths, on_progress=lambda n, total: calls.append((n, total))
    )
    assert report == validate_trajectories(paths)
    assert calls[0][0] == 0
    assert calls[-1][0] == calls[-1][1]


def test_dense_audit_cancellation_propagates():
    paths = {"A": [[0, 0, 0, 0], [1, 0, 0, 1]]}

    def cancel(*args):
        raise Cancelled

    with pytest.raises(Cancelled):
        audit_sampled_motion(paths, paths, on_progress=cancel)
