import importlib.util
import numpy as np

from collections import OrderedDict
from collections.abc import Callable, Iterable, MutableMapping, Sequence
from functools import wraps
from pathlib import Path
from typing import Any, Generic, TypeVar

from sbstudio.model.types import Coordinate3D


__all__ = (
    "consecutive_pairs",
    "constant",
    "create_path_and_open",
    "distance_sq_of",
    "get_skybrush_attr",
    "simplify_path",
)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def consecutive_pairs(
    iterable: Iterable[T], cyclic: bool = False
) -> Iterable[tuple[T, T]]:
    """Given an iterable, returns a generator that generates consecutive pairs
    of objects from the iterable.

    Args:
        iterable (Iterable[object]): the iterable to process
        cyclic (bool): whether the iterable should be considered "cyclic".
            If this argument is ``True``, the function will yield a pair
            consisting of the last element of the iterable paired with
            the first one at the end.
    """
    it = iter(iterable)
    try:
        prev = next(it)
    except StopIteration:
        return

    first = prev if cyclic else None
    try:
        while True:
            curr = next(it)
            yield prev, curr
            prev = curr
    except StopIteration:
        pass

    if cyclic:
        assert first is not None  # to help the type inference
        yield prev, first


def constant(value: Any) -> Callable[..., Any]:
    """Factory that returns a function that returns the given value when called
    with arbitrary arguments.
    """

    def result(*args, **kwds):
        return value

    return result


def create_path_and_open(filename, *args, **kwds):
    """Like open() but also creates the directories leading to the given file
    if they don't exist yet.
    """
    path = Path(filename)
    path.parent.mkdir(exist_ok=True, parents=True)
    return open(str(path), *args, **kwds)


def distance_sq_of(p: Coordinate3D, q: Coordinate3D) -> float:
    """Returns the squared Euclidean distance of two 3D points."""
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2


def get_ends(items: Iterable[T] | None) -> tuple[T, T] | None:
    """
    Returns the first and last item from the given iterable as a tuple if the
    iterable is not empty, otherwise returns `None`.

    If the iterable contains only one item, then first and last will be that one item.
    """
    if items is None:
        return None

    iterator = iter(items)
    try:
        first = last = next(iterator)
    except StopIteration:
        return None

    for item in iterator:
        last = item

    return (first, last)


def get_skybrush_attr(context, attr: str = "") -> Any | None:
    """Get skybrush or one of its attributes from the Blender context.

    Args:
        context: the Blender context to use
        attr: the attribute of skybrush to get or an empty string
            to get skybrush itself

    Returns:
        skybrush or its requested attribute, or `None` if not found
    """
    scene = getattr(context, "scene", None)
    skybrush = getattr(scene, "skybrush", None)

    if attr:
        return getattr(skybrush, attr, None)

    return skybrush


def negate(func: Callable[..., bool]) -> Callable[..., bool]:
    """Decorator that takes a function that returns a Boolean value and returns
    another function that returns the negation of the result of the original
    function.
    """

    @wraps(func)
    def new_func(*args, **kwds) -> bool:
        return not func(*args, **kwds)

    return new_func


DistanceFunc = Callable[[Iterable[T], T, T], Sequence[float]]
"""Type of a distance function used by `simplify_path`."""

EqFunc = Callable[[T, T], bool]
"""Type of an equality function used by `simplify_path`."""


def simplify_path(
    points: Sequence[T],
    *,
    eps: float,
    distance_func: DistanceFunc[T],
    eq_func: EqFunc[T],
) -> Sequence[T]:
    """Simplifies a sequence of points to a similar sequence with fewer
    points, using a distance function and an acceptable error term.

    The function uses the Ramer-Douglas-Peucker algorithm for simplifying the
    line segments.

    Parameters:
        points: a sequence of points. Each point may be an arbitrary object
            as long as the distance function can deal with it appropriately.
        eps: the error term; a point is considered redundant with
            respect to two other points if the point is closer to the line
            formed by the two other points than this error term.
        distance_func: a callable that receives a _list_ of points and two
            additional points, and returns the distance of _each_ point in the
            list from the line formed by the two additional points.
        eq_func: a callable that decides whether two points can be considered
            identical. This is used only in the early stage of the algorithm to
            identify constant segments.

    Returns:
        the simplified sequence of points. This will be of the same class as the
        input sequence. It is assumed that an instance of the sequence may be
        constructed from a list of items.
    """
    factory = points.__class__  # type: ignore

    if len(points) < 2:
        return factory(points)  # type: ignore

    assert eq_func is not None

    eq_with_next = np.array(
        [eq_func(u, v) for u, v in consecutive_pairs(points)], dtype=bool
    )

    to_keep = np.full(len(points), False)
    to_keep[0] = True
    to_keep[-1] = True
    to_keep[np.diff(eq_with_next).nonzero()[0] + 1] = True  # type: ignore

    result = []

    for start, end in consecutive_pairs(to_keep.nonzero()[0]):
        if not result:
            result.append(points[start])

        if not eq_with_next[start]:
            if eps > 0:
                _simplify_line(points, start, end, eps, distance_func, result)
            else:
                result.extend(points[(start + 1) : (end - 1)])

        result.append(points[end])

    return factory(result)  # type: ignore


def _simplify_line(
    points: Sequence[T],
    start: int,
    end: int,
    eps: float,
    distance_func: DistanceFunc,
    result: list[T],
) -> None:
    if end - start < 2:
        return

    dists = distance_func(points[start : (end + 1)], points[start], points[end])
    index = max(range(len(dists)), key=dists.__getitem__)
    dmax = dists[index]

    if dmax <= eps:
        return

    index += start

    result.append(points[index])
    _simplify_line(points, start, index, eps, distance_func, result)
    _simplify_line(points, index, end, eps, distance_func, result)


def load_module(path: str) -> Any:
    """Loads a module and returns it.

    Parameters:
        path: the path to the module.

    Returns:
        the loaded module.
    """
    spec = importlib.util.spec_from_file_location("colors_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LRUCache(Generic[K, V], MutableMapping[K, V]):
    """Size-limited cache with least-recently-used eviction policy."""

    _items: OrderedDict[K, V]

    def __init__(self, capacity: int):
        """Constructor.

        Parameters:
            capacity: maximum number of items that can be stored in the cache.
        """
        self._items = OrderedDict()
        self._capacity = max(int(capacity), 1)

    def __delitem__(self, key: K) -> None:
        del self._items[key]

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __setitem__(self, key: K, value: V):
        self._items[key] = value
        self._items.move_to_end(key)
        if len(self._items) > self._capacity:
            self._items.popitem(last=False)

    def get(self, key: K) -> V:
        """Returns the value corresponding to the given key, marking the key as
        recently accessed.
        """
        value = self._items[key]
        self._items.move_to_end(key)
        return value

    def peek(self, key: K) -> V:
        """Returns the value corresponding to the given key, _without_ marking
        the key as recently accessed.
        """
        return self._items[key]

    __getitem__ = peek
