"""Reusable O(N²) workspace for exact linear-interval distance minimization."""

import numpy as np


class PairwiseWorkspace:
    def __init__(self, count):
        self.pair_i, self.pair_j = np.triu_indices(count, k=1)
        size = len(self.pair_i)
        self.relative = np.empty((size, 3))
        self.delta = np.empty((size, 3))
        self.scratch = np.empty((size, 3))
        self.displacement = np.empty((count, 3))
        self.denominator = np.empty(size)
        self.offset = np.empty(size)
        self.squared = np.empty(size)

    def evaluate(self, start, end=None):
        """Return borrowed arrays (squared distance, fractional time).

        Results are overwritten by the next call. Every pair is checked;
        there is no approximate pruning or change in interval coverage.
        """
        # Indices come from triu_indices(count), so they are already in bounds.
        # clip avoids NumPy's extra output buffering used by mode='raise'.
        np.take(start, self.pair_i, axis=0, out=self.relative, mode="clip")
        np.take(start, self.pair_j, axis=0, out=self.scratch, mode="clip")
        np.subtract(self.relative, self.scratch, out=self.relative)
        self.offset.fill(0)
        if end is not None:
            np.subtract(end, start, out=self.displacement)
            np.take(self.displacement, self.pair_i, axis=0, out=self.delta, mode="clip")
            np.take(
                self.displacement, self.pair_j, axis=0, out=self.scratch, mode="clip"
            )
            np.subtract(self.delta, self.scratch, out=self.delta)
            np.einsum("ij,ij->i", self.delta, self.delta, out=self.denominator)
            np.einsum("ij,ij->i", self.relative, self.delta, out=self.offset)
            np.negative(self.offset, out=self.offset)
            moving = self.denominator > 0
            np.divide(self.offset, self.denominator, out=self.offset, where=moving)
            self.offset[~moving] = 0
            np.clip(self.offset, 0, 1, out=self.offset)
            np.multiply(self.delta, self.offset[:, None], out=self.delta)
            np.add(self.relative, self.delta, out=self.relative)
        np.einsum("ij,ij->i", self.relative, self.relative, out=self.squared)
        return self.squared, self.offset
