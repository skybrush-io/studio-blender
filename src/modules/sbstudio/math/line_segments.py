"""Algorithm to find the nearest points in a set of line segments."""

from numpy import array, dot, inf
from typing import Tuple

from sbstudio.model.types import Coordinate3D

__all__ = ("find_closest_points_on_line_segments",)


def _closest_points_on_two_line_segments(
    first, second, epsilon: float = 1e-6
) -> Tuple[float, Coordinate3D, Coordinate3D]:
    """Calculates the closest points on two line segments.

    Args:
        first: the first line segment as a numpy array
        second: the second line segment as a numpy array
        epsilon: threshold under which we treat numbers as zero

    Returns:
        tuple of the squared distance between closest points and the points
        themselves on the segments that are closest

    """
    # initialize variables
    p = first[0]
    q = second[0]
    u = first[1] - p
    v = second[1] - q
    w0 = p - q
    a = dot(u, u)
    b = dot(u, v)
    c = dot(v, v)
    d = dot(u, w0)
    e = dot(v, w0)
    # get denominator
    s = a * c - b * b
    # if lines are parallel
    if abs(s) < epsilon:
        if b != 0:
            t = d / b
        else:
            t = 0
    # if lines are not parallel
    else:
        t = (a * e - b * d) / s
        s = (b * e - c * d) / s
    # clamp s and t into [0;1] to remain on the line segment
    s = min(max(s, 0), 1)
    t = min(max(t, 0), 1)

    first = p + u * s
    second = q + v * t
    d = second - first
    distance = dot(d.T, d)

    return (distance, first, second)


def find_closest_points_on_line_segments(lines):
    """Finds the closest point pair in a given set of line segments using the
    standard Euclidean distance norm.

    Parameters:
        lines: the input, either as a list-of-line-segments where each line
            segment may be a tuple or a list, or as a NumPy array where each row
            is two points

    Returns:
        the coordinates of the first and the second point in the closest point
        pair on the line segments and their distance
    """
    lines = array(lines, dtype=float)
    n = lines.shape[0]
    if n < 2:
        # we only have one line segment
        return None, inf

    # calculate bounding boxes of all tethers
    bboxes = [
        [[min(a, b), max(a, b)] for a, b in zip(line[0], line[1])] for line in lines
    ]
    # calculate all distances in a brute force method
    # TODO: optimize code to avoid for loops where possible
    min_distance_sq = inf
    min_distance = inf
    closest_points = None
    for i in range(n - 1):
        for j in range(i + 1, n):
            # first check bounding box, if they are far away, there is no
            # need to perform more cpu-intensive calculations
            if all(
                bboxes[i][k][0] < bboxes[j][k][1] + min_distance
                and bboxes[j][k][0] < bboxes[i][k][1] + min_distance
                for k in range(3)
            ):
                # if needed, check accurate distance
                distance_sq, p, q = _closest_points_on_two_line_segments(
                    lines[i], lines[j]
                )
                if distance_sq < min_distance_sq:
                    min_distance_sq = distance_sq
                    min_distance = min_distance_sq ** 0.5
                    closest_points = (p, q)

    return closest_points, min_distance
