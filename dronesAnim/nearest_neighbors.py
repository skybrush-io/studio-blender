"""Drone Anim's indexed adaptation of Skybrush's nearest-neighbor algorithms.

Based on ``sbstudio.math.nearest_neighbors``. Indices are retained so that
coincident points still identify distinct drones.
"""

import numpy as np


def _reorder_along_principal_axis(points):
    """Return point indices sorted along the widest coordinate axis."""
    principal_axis = int(np.ptp(points, axis=0).argmax())
    order = np.argsort(points[:, principal_axis], kind="stable")
    return order, principal_axis


def _distance_sq_matrix(first, second):
    return np.sum((first[:, np.newaxis, :] - second[np.newaxis, :, :]) ** 2, axis=-1)


def _nearest_neighbors_divide_and_conquer_step(points, order, axis):
    count = len(order)
    if count < 2:
        return None, float("inf")
    if count <= 100:
        distances = _distance_sq_matrix(points[order], points[order])
        np.fill_diagonal(distances, np.inf)
        first, second = np.unravel_index(distances.argmin(), distances.shape)
        return (int(order[first]), int(order[second])), float(distances[first, second])

    midpoint_index = count // 2
    midpoint = points[order[midpoint_index], axis]
    left_pair, left_distance = _nearest_neighbors_divide_and_conquer_step(
        points, order[:midpoint_index], axis
    )
    right_pair, right_distance = _nearest_neighbors_divide_and_conquer_step(
        points, order[midpoint_index:], axis
    )
    if left_distance <= right_distance:
        pair, distance = left_pair, left_distance
    else:
        pair, distance = right_pair, right_distance
    if distance == 0:
        return pair, distance

    coordinates = points[order, axis]
    radius = distance**0.5
    lo = np.searchsorted(coordinates, midpoint - radius, side="left")
    hi = np.searchsorted(coordinates, midpoint + radius, side="right")
    left = order[lo:midpoint_index]
    right = order[midpoint_index:hi]

    # Bound temporary matrices when a wide split contains many points.
    for left_start in range(0, len(left), 256):
        left_block = left[left_start : left_start + 256]
        for right_start in range(0, len(right), 256):
            right_block = right[right_start : right_start + 256]
            distances = _distance_sq_matrix(points[left_block], points[right_block])
            first, second = np.unravel_index(distances.argmin(), distances.shape)
            candidate = float(distances[first, second])
            if candidate < distance:
                pair = (int(left_block[first]), int(right_block[second]))
                distance = candidate
                if distance == 0:
                    return pair, distance
    return pair, distance


def find_nearest_neighbors(points, order=None, axis=None):
    """Return the indices and distance of the closest pair of points."""
    if len(points) < 2:
        return None, None
    if order is None or axis is None:
        order, axis = _reorder_along_principal_axis(points)
    pair, distance_sq = _nearest_neighbors_divide_and_conquer_step(points, order, axis)
    return pair, distance_sq**0.5


def find_all_point_pairs_closer_than(points, threshold, order=None, axis=None):
    """Return index pairs whose distance is strictly less than threshold."""
    if len(points) < 2 or threshold <= 0:
        return []
    if order is None or axis is None:
        order, axis = _reorder_along_principal_axis(points)

    coordinates = points[order, axis]
    # Include rounded boundary candidates; the distance test below remains strict.
    ends = np.searchsorted(
        coordinates, np.nextafter(coordinates + threshold, np.inf), side="right"
    )
    threshold_sq = threshold**2
    pairs = []
    for i, end in enumerate(ends):
        if end <= i + 1:
            continue
        others = order[i + 1 : end]
        delta = points[others] - points[order[i]]
        distances = np.sum(delta * delta, axis=1)
        first = int(order[i])
        for second in others[distances < threshold_sq]:
            second = int(second)
            pairs.append((min(first, second), max(first, second)))
    pairs.sort()
    return pairs


def find_proximity_pairs(points, threshold, *, all_pairs=True):
    """Find the closest pair and, optionally, all pairs below the threshold."""
    points = np.asarray(points, dtype=float)
    if len(points) < 2:
        return None, None, []
    order, axis = _reorder_along_principal_axis(points)
    closest, distance = find_nearest_neighbors(points, order, axis)
    close_pairs = (
        find_all_point_pairs_closer_than(points, threshold, order, axis)
        if all_pairs
        else []
    )
    return closest, distance, close_pairs
