import importlib.util

from collections import OrderedDict
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Callable, List, Sequence, TypeVar

from sbstudio.model.types import Coordinate3D


__all__ = (
    "constant",
    "create_path_and_open",
    "distance_sq_of",
    "simplify_path",
)

T = TypeVar("T")


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


def simplify_path(
    points: Sequence[T], *, eps: float, distance_func: Callable[[List[T], T, T], float]
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

    Returns:
        the simplified sequence of points. This will be of the same class as the
        input sequence. It is assumed that an instance of the sequence may be
        constructed from a list of items.
    """
    if not points:
        result = []
    else:
        # TODO(ntamas): find constant segments and keep those first
        result = _simplify_line(points, eps=eps, distance_func=distance_func)

    return points.__class__(result)


def _simplify_line(points, *, eps, distance_func):
    start, end = points[0], points[-1]
    dists = distance_func(points, start, end)
    index = max(range(len(dists)), key=dists.__getitem__)
    dmax = dists[index]

    if dmax <= eps:
        return [start, end]
    else:
        pre = _simplify_line(points[: index + 1], eps=eps, distance_func=distance_func)
        post = _simplify_line(points[index:], eps=eps, distance_func=distance_func)
        return pre[:-1] + post


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

class LRUCache(MutableMapping):
    """Size-limited cache with least-recently-used eviction policy."""

    def __init__(self, capacity: int):
        """Constructor.

        Parameters:
            capacity: maximum number of items that can be stored in the cache.
        """
        self._items = OrderedDict()
        self._capacity = max(int(capacity), 1)

    def __delitem__(self, key):
        del self._items[key]

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __setitem__(self, key, value):
        self._items[key] = value
        self._items.move_to_end(key)
        if len(self._items) > self._capacity:
            self._items.popitem(last=False)

    def get(self, key):
        """Returns the value corresponding to the given key, marking the key as
        recently accessed.
        """
        value = self._items[key]
        self._items.move_to_end(key)
        return value

    def peek(self, key):
        """Returns the value corresponding to the given key, _without_ marking
        the key as recently accessed.
        """
        return self._items[key]

    __getitem__ = peek
