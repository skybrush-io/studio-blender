"""Classes and functions related to random number generation."""

from collections.abc import Callable, Sequence
from random import Random
from threading import Lock
from typing import Self, overload

from numpy import array, concatenate, int_
from numpy.typing import NDArray

_GROWTH_BLOCK_SIZE = 4096
"""Block size used when growing the internal cache beyond 4096 elements."""


class RandomSequence(Sequence[int]):
    """Thread-safe random sequence class where individual items are cached and
    can be accessed by indexing.
    """

    _cache: NDArray[int_]
    """Cached items of the sequence that were already generated."""

    _max: int
    """Maximum value that can be returned in the sequence."""

    _rng: Random
    """Internal RNG that generates the sequence."""

    _rng_factory: Callable[[int | None], Random]
    """Factory function that created the internal RNG of this sequence, used
    for forking.
    """

    _lock: Lock
    """Lock that guarantees that only one thread is allowed to extend the
    cached items of the sequence.
    """

    def __init__(
        self,
        *,
        seed: int | None = None,
        max: int = 0xFFFFFFFF,
        rng_factory: Callable[[int | None], Random] = Random,
    ):
        """Constructor.

        Args:
            seed: the seed to use; ``None`` to use a random seed
            max: the maximum value in the sequence (the minimum is always 0)
            rng_factory: a function that can be called with a seed or ``None``
                and that returns an instance of Random_ to use. ``None`` must
                be interpreted by the function as "use a random seed".
        """
        self._cache = array([], dtype=int_)
        self._rng_factory = rng_factory
        self._rng = rng_factory(seed)
        self._max = max
        self._lock = Lock()

    @overload
    def __getitem__(self, index: int) -> int: ...
    @overload
    def __getitem__(self, index: slice) -> list[int]: ...

    def __getitem__(self, index: int | slice) -> int | list[int]:
        if isinstance(index, slice):
            return self._get_slice(index)
        if len(self._cache) <= index:
            self._ensure_length_is_at_least(index + 1)
        return int(self._cache[index])

    def _get_slice(self, index: slice) -> list[int]:
        start, stop, step = index.start, index.stop, index.step
        if start is None:
            start = 0
        if step is None:
            step = 1
        if stop is None:
            raise TypeError("RandomSequence slice requires an explicit stop value")
        if start < 0 or stop < 0:
            raise IndexError(
                "Negative slice indices are not supported for RandomSequence"
            )
        if stop > len(self._cache):
            self._ensure_length_is_at_least(stop)
        return self._cache[start:stop:step].tolist()

    def __len__(self) -> int:
        return len(self._cache)

    def _ensure_length_is_at_least(self, length: int) -> None:
        with self._lock:
            current = len(self._cache)
            if current < length:
                target = self._compute_target_size(length)
                extra = target - current
                new_values = array(
                    [self._rng.randint(0, self._max) for _ in range(extra)],
                    dtype=int_,
                )
                self._cache = concatenate([self._cache, new_values])

    @staticmethod
    def _compute_target_size(minimum: int) -> int:
        if minimum <= _GROWTH_BLOCK_SIZE:
            return 1 << (minimum - 1).bit_length()
        return ((minimum - 1) // _GROWTH_BLOCK_SIZE + 1) * _GROWTH_BLOCK_SIZE

    def fork(self, index: int) -> Self:
        """Forks off a new random sequence from the given index such that the
        new sequence is seeded by the number at the given index in this sequence.
        """
        return self.__class__(
            seed=self[index], max=self._max, rng_factory=self._rng_factory
        )

    def get(self, index: int) -> int:
        """Returns the random number at the given index in the sequence."""
        return self[index]

    def get_array(self, start: int, length: int) -> NDArray[int_]:
        """Returns a NumPy array of the given length containing the random
        numbers from ``start`` onward in the sequence.

        Args:
            start: the starting index (must be non-negative)
            length: the number of elements to return

        Returns:
            a NumPy array of shape ``(length,)`` with dtype int
        """
        stop = start + length
        if stop > len(self._cache):
            self._ensure_length_is_at_least(stop)
        return self._cache[start:stop].copy()

    def get_float(self, index: int) -> float:
        """Returns the random number at the given index in the sequence, divided
        by the maximum number that could theoretically be there, effectively
        producing a float between 0 and 1, inclusive.
        """
        return self[index] / self.max

    @property
    def max(self) -> int:
        """Returns the maximum value that can be returned in the random sequence."""
        return self._max
