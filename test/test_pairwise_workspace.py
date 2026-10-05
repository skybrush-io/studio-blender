import numpy as np
import pytest
from sbstudio.math.pairwise_workspace import PairwiseWorkspace


def reference(start, end):
    i, j = np.triu_indices(len(start), k=1)
    relative = start[i] - start[j]
    offset = np.zeros(len(i))
    if end is not None:
        displacement = end - start
        delta = displacement[i] - displacement[j]
        denominator = np.einsum("ij,ij->i", delta, delta)
        offset = np.clip(
            np.divide(
                -np.einsum("ij,ij->i", relative, delta),
                denominator,
                out=np.zeros_like(denominator),
                where=denominator > 0,
            ),
            0,
            1,
        )
        relative = relative + offset[:, None] * delta
    return np.einsum("ij,ij->i", relative, relative), offset


@pytest.mark.parametrize("count", [1, 2, 10, 100, 500])
def test_reused_workspace_matches_original_formula(count):
    rng = np.random.default_rng(812)
    workspace = PairwiseWorkspace(count)
    for trial in range(8):
        start = rng.normal(size=(count, 3)) * 30
        end = start.copy() if trial % 3 == 0 else rng.normal(size=(count, 3)) * 30
        if trial == 7:
            end = None
        actual = workspace.evaluate(start, end)
        expected = reference(start, end)
        for a, b in zip(actual, expected):
            np.testing.assert_array_equal(a, b)
