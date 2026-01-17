"""Classes and functions related to random number generation."""

from random import Random
from threading import Lock
from typing import Callable, Optional, Sequence, TypeVar


C = TypeVar("C", bound="RandomSequence")


class RandomSequence(Sequence[int]):
    """Thread-safe random sequence class where individual items are cached and
    can be accessed by indexing.
    """

    _cache: list[int]
    """Cached items of the sequence that were already generated."""

    _max: int
    """Maximum value that can be returned in the sequence."""

    _rng: Random
    """Internal RNG that generates the sequence."""

    _rng_factory: Callable[[Optional[int]], Random]
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
        seed: Optional[int] = None,
        max: int = 0xFFFFFFFF,
        rng_factory: Callable[[Optional[int]], Random] = Random,
    ):
        """Constructor.

        Args:
            seed: the seed to use; ``None`` to use a random seed
            max: the maximum value in the sequence (the minimum is always 0)
            rng_factory: a function that can be called with a seed or ``None``
                and that returns an instance of Random_ to use. ``None`` must
                be interpreted by the function as "use a random seed".
        """
        self._cache = []
        self._rng_factory = rng_factory
        self._rng = rng_factory(seed)
        self._max = max
        self._lock = Lock()

    def __getitem__(self, index: int) -> int:
        if len(self._cache) <= index:
            self._ensure_length_is_at_least(index + 1)
        return self._cache[index]

    def __len__(self) -> int:
        return len(self._cache)

    def _ensure_length_is_at_least(self, length: int) -> None:
        with self._lock:
            while len(self._cache) < length:
                self._cache.append(self._rng.randint(0, self._max))

    def fork(self: C, index: int) -> C:
        """Forks off a new random sequence from the given index such that the
        new sequence is seeded by the number at the given index in this sequence.
        """
        return self.__class__(
            seed=self[index], max=self._max, rng_factory=self._rng_factory
        )

    def get(self, index: int) -> int:
        """Returns the random number at the given index in the sequence."""
        return self[index]

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
