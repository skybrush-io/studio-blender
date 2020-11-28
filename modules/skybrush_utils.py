"""All kinds of handy utils to be used by the converter."""

from pathlib import Path
from typing import Any, Callable, List, Sequence


__all__ = ["create_path_and_open", "simplify_path"]


def create_path_and_open(filename, *args, **kwds):
    """Like open() but also creates the directories leading to the given file
    if they don't exist yet.
    """
    if not isinstance(filename, Path):
        path = Path(filename)
    else:
        path = filename

    path.parent.mkdir(exist_ok=True, parents=True)
    return open(str(path), *args, **kwds)


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
