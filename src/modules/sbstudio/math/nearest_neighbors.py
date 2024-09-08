"""Algorithm to find the nearest neighbors in a set of points."""

from numpy import array, fill_diagonal, inf, newaxis, nonzero, ptp, searchsorted, sum

__all__ = ("find_nearest_neighbors",)


def _get_distance_sq_matrix(points):
    """Returns a matrix containing the squares of the Euclidean distances
    between all possible pairs of the given points.

    Parameters:
        points (array): a NumPy array where each row is a point
    """
    return sum((points[:, newaxis, :] - points[newaxis, :, :]) ** 2, axis=-1)


def _get_distance_sq_matrix_pairs(first, second):
    """Returns a matrix containing the squares of the Euclidean distances
    between all possible pairs of the given source and target points.

    Parameters:
        first (array): the source NumPy array where each row is a point
        second (array): the target NumPy array where each row is a point
    """
    return sum((first[:, newaxis, :] - second[newaxis, :, :]) ** 2, axis=-1)


def _nearest_neighbors_brute_force(points):
    """Finds the nearest neighbors in a 2D or 3D point set given as a NumPy
    array (one point per row), using an O(n^2) brute-force algorithm.
    """
    num_points, _ = points.shape
    if num_points < 2:
        # Trivial case
        return None, None, inf

    dist_sq_matrix = _get_distance_sq_matrix(points)
    fill_diagonal(dist_sq_matrix, inf)
    first, second = divmod(dist_sq_matrix.argmin(), num_points)

    return points[first], points[second], dist_sq_matrix[first, second] ** 0.5


def _reorder_along_principal_axis(points):
    """Given a list of points, finds the principal axis along which the dataset
    is the "widest" and then sorts the points in ascending order along this
    axis.

    Returns:
        the sorted points and the index of the principal axis
    """
    principal_axis = ptp(points, axis=0).argmax()
    points = points[points[:, principal_axis].argsort(), :]
    return points, principal_axis


def _nearest_neighbors_divide_and_conquer(points):
    """Finds the nearest neighbors in a 2D or 3D point set given as a NumPy
    array (one point per row), using an O(n log(n) log(n)) divide-and-conquer
    algorithm.
    """
    num_points, _ = points.shape
    if num_points < 2:
        return None, None, inf

    # Find the principal axis along which the dataset is the "widest"
    points, principal_axis = _reorder_along_principal_axis(points)
    p, q, dist_sq = _nearest_neighbors_divide_and_conquer_step(points, principal_axis)
    return p, q, dist_sq**0.5


def _nearest_neighbors_divide_and_conquer_step(points, principal_axis):
    num_points, _ = points.shape

    if num_points < 2:
        # trivial case
        return None, None, inf
    elif num_points <= 100:
        # case is small enough so it is not worth dividing it further
        dist_sq_matrix = _get_distance_sq_matrix(points)
        fill_diagonal(dist_sq_matrix, inf)
        first, second = divmod(dist_sq_matrix.argmin(), dist_sq_matrix.shape[0])
        return points[first], points[second], dist_sq_matrix[first, second]

    mid_index = num_points // 2
    midpoint = points[mid_index, principal_axis]

    # Divide-and conquer step: find the closest points in the left and right
    # half of the problem
    p1, q1, dist_sq1 = _nearest_neighbors_divide_and_conquer_step(
        points[:mid_index, :], principal_axis
    )
    p2, q2, dist_sq2 = _nearest_neighbors_divide_and_conquer_step(
        points[mid_index:, :], principal_axis
    )
    if dist_sq1 < dist_sq2:
        closest_nonsplit_solution = p1, q1, dist_sq1
        dist_sq_nonsplit = dist_sq1
    else:
        closest_nonsplit_solution = p2, q2, dist_sq2
        dist_sq_nonsplit = dist_sq2

    # Look for any potential improvements _between_ the two halves
    p3, q3, dist_sq_split = _nearest_neighbors_find_closest_split_pair(
        points, principal_axis, mid_index, midpoint, dist_sq_nonsplit**0.5
    )
    if dist_sq_nonsplit <= dist_sq_split:
        return closest_nonsplit_solution
    else:
        return p3, q3, dist_sq_split


def _nearest_neighbors_find_closest_split_pair(
    points, principal_axis, mid_index, midpoint, dist
):
    xs = points[:, principal_axis]
    lo = searchsorted(xs, midpoint - dist, side="left")
    hi = searchsorted(xs, midpoint + dist, side="right")
    if lo == mid_index or hi == mid_index:
        return None, None, inf

    left = points[lo:mid_index, :]
    right = points[mid_index:hi, :]

    dist_sq_matrix = _get_distance_sq_matrix_pairs(left, right)
    first, second = divmod(dist_sq_matrix.argmin(), dist_sq_matrix.shape[1])
    return left[first], right[second], dist_sq_matrix[first, second]


def find_nearest_neighbors(points):
    """Finds the closest point pair in a given point set using the standard
    Euclidean distance norm.

    Parameters:
        points: the input, either as a list-of-points where each point may be
            a tuple or a list, or as a NumPy array where each row is a point

    Returns:
        the coordinates of the first and the second point in the closest point
        pair, and their distance
    """
    if not points:
        # we have no points
        return None, None, inf

    points = array(points, dtype=float)
    if points.shape[0] < 2:
        # we have less than two points
        return None, None, inf

    return _nearest_neighbors_divide_and_conquer(points)


def find_all_point_pairs_closer_than(points, threshold):
    """Finds all point pairs that are closer than the given threshold.

    This is a slow brute-force algorithm, but it does not have to be executed
    frequently so it is probably okay.

    Parameters:
        points: the input, either as a list-of-points where each point may be
            a tuple or a list, or as a NumPy array where each row is a point

    Returns:
        the coordinate pairs representing all pairs of points that are closer
        than the given threshold
    """
    result = []
    if not points:
        # we have no points
        return result

    points = array(points, dtype=float)

    num_points, _ = points.shape
    if num_points < 2:
        return result

    threshold_sq = threshold**2
    points, principal_axis = _reorder_along_principal_axis(points)
    for i, p in enumerate(points):
        max_coord = p[principal_axis] + threshold
        end = None
        for j, q in enumerate(points[i + 1 :]):
            if q[principal_axis] >= max_coord:
                end = i + j + 1

        dsq = _get_distance_sq_matrix_pairs(points[i : i + 1], points[i + 1 : end])[0]
        qs = points[nonzero(dsq < threshold_sq)[0] + i + 1]

        result.extend((p, q) for q in qs)

    return result


def test():
    points = array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
    print(find_all_point_pairs_closer_than(points, 6))


if __name__ == "__main__":
    test()
