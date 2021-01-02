from collections import OrderedDict
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Tuple


__all__ = (
    "constant",
    "create_path_and_open",
    "get_moves_required_to_sort_collection",
    "simplify_path",
)


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


def get_moves_required_to_sort_collection(
    items: Sequence[Any], key: Optional[Callable[[Any], Any]] = None
) -> List[Tuple[int, int]]:
    """Given a list of items and an optional sorting key function, returns a
    list of from-to pairs representing steps that are needed to sort the list
    with single-item moves. This is useful for sorting Blender collections
    with its `move()` method.
    """
    result = []
    num_items = len(items)

    if num_items:
        if key:
            items = [key(item) for item in items]

        indexes = sorted(range(num_items), key=items.__getitem__)

        for front, index in enumerate(indexes):
            if index != front:
                result.append((index, front))
                for j in range(front + 1, num_items):
                    if indexes[j] >= front and indexes[j] < index:
                        indexes[j] += 1

    return result


# >>> print(get_moves_required_to_sort_collection([10, 40, 30, 20, 50]))
# [(3, 1), (3, 2)]
# >>> print(get_moves_required_to_sort_collection([30, 20, 10, 40]))
# [(2, 0), (2, 1)]
# print(get_moves_required_to_sort_collection([50, 70, 40, 30, 20, 60, 10]))
# [(6, 0), (5, 1), (5, 2), (5, 3), (6, 5)]


def simplify_path(
    points: Sequence[Any],
    *,
    eps: float,
    distance_func: Callable[[List[Any], Any, Any], float]
) -> Sequence[Any]:
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
        distance_func: a
            callable that receives a _list_ of points and two additional
            points, and returns the distance of _each_ point in the list
            from the line formed by the two additional points.

    Returns:
        : the simplified sequence of points. This will be of the
            same class as the input sequence. It is assumed that an instance of
            the sequence may be constructed from a list of items.
    """
    if not points:
        result = []
    else:
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
