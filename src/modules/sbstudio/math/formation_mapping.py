import numpy as np
# import sys
# import site
# sys.path.insert(0,site.USER_SITE)
# from optimize import linear_sum_assignment as lsa
# import scipy.optimize
import math
def linear_sum_assignment(cost_matrix, maximize=False):
    """Solve the linear sum assignment problem.
    The linear sum assignment problem is also known as minimum weight matching
    in bipartite graphs. A problem instance is described by a matrix C, where
    each C[i,j] is the cost of matching vertex i of the first partite set
    (a "worker") and vertex j of the second set (a "job"). The goal is to find
    a complete assignment of workers to jobs of minimal cost.
    Formally, let X be a boolean matrix where :math:`X[i,j] = 1` iff row i is
    assigned to column j. Then the optimal assignment has cost
    .. math::
        \min \sum_i \sum_j C_{i,j} X_{i,j}
    s.t. each row is assignment to at most one column, and each column to at
    most one row.
    This function can also solve a generalization of the classic assignment
    problem where the cost matrix is rectangular. If it has more rows than
    columns, then not every row needs to be assigned to a column, and vice
    versa.
    The method used is the Hungarian algorithm, also known as the Munkres or
    Kuhn-Munkres algorithm.
    Parameters
    ----------
    cost_matrix : array
        The cost matrix of the bipartite graph.
    maximize    : boolean
        Indicator of whether to solve for minimum cost matrix (default: False) or the maximum (True)
        
        
    Returns
    -------
    row_ind, col_ind : array
        An array of row indices and one of corresponding column indices giving
        the optimal assignment. The cost of the assignment can be computed
        as ``cost_matrix[row_ind, col_ind].sum()``. The row indices will be
        sorted; in the case of a square cost matrix they will be equal to
        ``numpy.arange(cost_matrix.shape[0])``.
    Notes
    -----
    .. versionadded:: 0.17.0
    Examples
    --------
    >>> cost = np.array([[4, 1, 3], [2, 0, 5], [3, 2, 2]])
    >>> from scipy.optimize import linear_sum_assignment
    >>> row_ind, col_ind = linear_sum_assignment(cost)
    >>> col_ind
    array([1, 0, 2])
    >>> cost[row_ind, col_ind].sum()
    5
    References
    ----------
    1. http://csclab.murraystate.edu/bob.pilgrim/445/munkres.html
    2. Harold W. Kuhn. The Hungarian Method for the assignment problem.
       *Naval Research Logistics Quarterly*, 2:83-97, 1955.
    3. Harold W. Kuhn. Variants of the Hungarian method for assignment
       problems. *Naval Research Logistics Quarterly*, 3: 253-258, 1956.
    4. Munkres, J. Algorithms for the Assignment and Transportation Problems.
       *J. SIAM*, 5(1):32-38, March, 1957.
    5. https://en.wikipedia.org/wiki/Hungarian_algorithm
    """
    cost_matrix = np.asarray(cost_matrix)
    if len(cost_matrix.shape) != 2:
        raise ValueError("expected a matrix (2-d array), got a %r array"
                         % (cost_matrix.shape,))

    # The algorithm expects more columns than rows in the cost matrix.
    if cost_matrix.shape[1] < cost_matrix.shape[0]:
        cost_matrix = cost_matrix.T
        transposed = True
    else:
        transposed = False

    state = _Hungary(cost_matrix, maximize)

    # No need to bother with assignments if one of the dimensions
    # of the cost matrix is zero-length.
    step = None if 0 in cost_matrix.shape else _step1

    while step is not None:
        step = step(state)

    if transposed:
        marked = state.marked.T
    else:
        marked = state.marked
    return np.where(marked == 1)


class _Hungary(object):
    """State of the Hungarian algorithm.
    Parameters
    ----------
    cost_matrix : 2D matrix
        The cost matrix. Must have shape[1] >= shape[0].
    """

    def __init__(self, cost_matrix, maximize):
        self.C = cost_matrix.copy()

        n, m = self.C.shape
        self.row_uncovered = np.ones(n, dtype=bool)
        self.col_uncovered = np.ones(m, dtype=bool)
        self.Z0_r = 0
        self.Z0_c = 0
        self.path = np.zeros((n + m, 2), dtype=int)
        self.marked = np.zeros((n, m), dtype=int)
        self.maximize = maximize

    def _clear_covers(self):
        """Clear all covered matrix cells"""
        self.row_uncovered[:] = True
        self.col_uncovered[:] = True


# Individual steps of the algorithm follow, as a state machine: they return
# the next step to be taken (function to be called), if any.

def _step1(state):
    """Steps 1 and 2 in the Wikipedia page."""

    # Step 1: For each row of the matrix, find the smallest element and
    # subtract it from every element in its row.
    if state.maximize:
        state.C -= state.C.max(axis=1)[:, np.newaxis]
    else:
        state.C -= state.C.min(axis=1)[:, np.newaxis]
    # Step 2: Find a zero (Z) in the resulting matrix. If there is no
    # starred zero in its row or column, star Z. Repeat for each element
    # in the matrix.
    for i, j in zip(*np.where(state.C == 0)):
        if state.col_uncovered[j] and state.row_uncovered[i]:
            state.marked[i, j] = 1
            state.col_uncovered[j] = False
            state.row_uncovered[i] = False

    state._clear_covers()
    return _step3


def _step3(state):
    """
    Cover each column containing a starred zero. If n columns are covered,
    the starred zeros describe a complete set of unique assignments.
    In this case, Go to DONE, otherwise, Go to Step 4.
    """
    marked = (state.marked == 1)
    state.col_uncovered[np.any(marked, axis=0)] = False

    if marked.sum() < state.C.shape[0]:
        return _step4


def _step4(state):
    """
    Find a noncovered zero and prime it. If there is no starred zero
    in the row containing this primed zero, Go to Step 5. Otherwise,
    cover this row and uncover the column containing the starred
    zero. Continue in this manner until there are no uncovered zeros
    left. Save the smallest uncovered value and Go to Step 6.
    """
    # We convert to int as numpy operations are faster on int
    C = (state.C == 0).astype(int)
    covered_C = C * state.row_uncovered[:, np.newaxis]
    covered_C *= np.asarray(state.col_uncovered, dtype=int)
    n = state.C.shape[0]
    m = state.C.shape[1]

    while True:
        # Find an uncovered zero
        row, col = np.unravel_index(np.argmax(covered_C), (n, m))
        if covered_C[row, col] == 0:
            return _step6
        else:
            state.marked[row, col] = 2
            # Find the first starred element in the row
            star_col = np.argmax(state.marked[row] == 1)
            if state.marked[row, star_col] != 1:
                # Could not find one
                state.Z0_r = row
                state.Z0_c = col
                return _step5
            else:
                col = star_col
                state.row_uncovered[row] = False
                state.col_uncovered[col] = True
                covered_C[:, col] = C[:, col] * (
                    np.asarray(state.row_uncovered, dtype=int))
                covered_C[row] = 0


def _step5(state):
    """
    Construct a series of alternating primed and starred zeros as follows.
    Let Z0 represent the uncovered primed zero found in Step 4.
    Let Z1 denote the starred zero in the column of Z0 (if any).
    Let Z2 denote the primed zero in the row of Z1 (there will always be one).
    Continue until the series terminates at a primed zero that has no starred
    zero in its column. Unstar each starred zero of the series, star each
    primed zero of the series, erase all primes and uncover every line in the
    matrix. Return to Step 3
    """
    count = 0
    path = state.path
    path[count, 0] = state.Z0_r
    path[count, 1] = state.Z0_c

    while True:
        # Find the first starred element in the col defined by
        # the path.
        row = np.argmax(state.marked[:, path[count, 1]] == 1)
        if state.marked[row, path[count, 1]] != 1:
            # Could not find one
            break
        else:
            count += 1
            path[count, 0] = row
            path[count, 1] = path[count - 1, 1]

        # Find the first prime element in the row defined by the
        # first path step
        col = np.argmax(state.marked[path[count, 0]] == 2)
        if state.marked[row, col] != 2:
            col = -1
        count += 1
        path[count, 0] = path[count - 1, 0]
        path[count, 1] = col

    # Convert paths
    for i in range(count + 1):
        if state.marked[path[i, 0], path[i, 1]] == 1:
            state.marked[path[i, 0], path[i, 1]] = 0
        else:
            state.marked[path[i, 0], path[i, 1]] = 1

    state._clear_covers()
    # Erase all prime markings
    state.marked[state.marked == 2] = 0
    return _step3


def _step6(state):
    """
    Add the value found in Step 4 to every element of each covered row,
    and subtract it from every element of each uncovered column.
    Return to Step 4 without altering any stars, primes, or covered lines.
    """
    # the smallest uncovered value in the matrix
    if np.any(state.row_uncovered) and np.any(state.col_uncovered):
        if state.maximize:
            minval = np.max(state.C[state.row_uncovered], axis=0)
            minval = np.max(minval[state.col_uncovered])
        else:
            minval = np.min(state.C[state.row_uncovered], axis=0)
            minval = np.min(minval[state.col_uncovered])            
        state.C[~state.row_uncovered] += minval
        state.C[:, state.col_uncovered] -= minval
    return _step4
    
class cost_block:
    x = 0
    y = 0
    cost = 0

def getCost(self):
        return self.cost

def hall_condition_check(cost_mat, bigNum):
    row_ind, col_ind = linear_sum_assignment(cost_mat)
    for item in cost_mat[row_ind, col_ind]:
        if item == bigNum:
            return False
    return True

#cost function that should be used to create cost matrix
def square_euclidean_cost(coord1, coord2):
    return (coord1[0]-coord2[0])**2 + (coord1[1]-coord2[1])**2 + (coord1[2]-coord2[2])**2

def euclidean_cost(coord1, coord2):
    return ((coord1[0]-coord2[0])**2 + (coord1[1]-coord2[1])**2 + (coord1[2]-coord2[2])**2)**0.5

def exponential_cost(coord1, coord2):
    return 2**((coord1[0]-coord2[0])**2 + (coord1[1]-coord2[1])**2 + (coord1[2]-coord2[2])**2)

#function that calculates cost matrix
def cost_matrix_calc(formation1, formation2, costFunction):
    n = formation1.shape[0]
    cost_matrix = np.zeros((n,n))
    for coordIndex1, coord1 in enumerate(formation1):
        for coordIndex2, coord2 in enumerate(formation2):
            cost_matrix[coordIndex1][coordIndex2] = costFunction(coord1, coord2)
    return cost_matrix  

#function that provides optimum mapping with respect to cost function with regular hungarian algorithm
def smart_transition_mapper(formation1, formation2, costFunction):
    cost_matrix = cost_matrix_calc(formation1, formation2, costFunction)
    original_cost_matrix = cost_matrix_calc(formation1, formation2, euclidean_cost)
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    mapping_order = col_ind
    #min_cost = cost_matrix[row_ind, col_ind].sum()
    min_cost = np.amax(original_cost_matrix[row_ind, col_ind])
    return mapping_order, min_cost

#function that provides optimum mapping with respect to cost function with fair-hungarian algorithm
def optimal_transition_mapper(formation1, formation2):
    cost_matrix = cost_matrix_calc(formation1, formation2, euclidean_cost)
    distances = []
    for idx, itemx in enumerate(cost_matrix):
        for idy, itemy in enumerate(itemx):
            block = cost_block()
            block.x = idx
            block.y = idy
            block.cost = itemy
            distances.append(block)
    distances.sort(key=getCost)
    l = 1
    r = len(distances)
    while l!=r:
        m = math.ceil((l + r)/2)
        E0 = []
        for item in distances:
            if item.cost > distances[m - 1].cost:
                E0.append(item)
        m_copy = cost_matrix.copy()
        biggest_cell = max(map(max,m_copy))
        for item in E0:
            m_copy[item.x][item.y] = biggest_cell + 1
        if hall_condition_check(m_copy, biggest_cell + 1) == True:
            r = m - 1
        else:
            l = m
        E0 = []
    for item in distances:
            if item.cost > distances[l].cost:
                E0.append(item)
    m_copy = cost_matrix.copy()
    for item in E0:
        m_copy[item.x][item.y] = 10**6
    row_ind, col_ind = linear_sum_assignment(m_copy)
    cost = np.amax(cost_matrix[row_ind, col_ind])
    order = col_ind
    return order, cost

#grid formation creator just for testing purpose
def create_grid_formation(x, y, height, spacing):
    formation = np.zeros((x*y,3))
    bias_x = (x-1)*spacing/2
    bias_y = (y-1)*spacing/2
    for i in range(x):
        for j in range(y):
            formation[i*x+j][0] = i*spacing - bias_x
            formation[i*x+j][1] = j*spacing -bias_y
            formation[i*x+j][2] = height
    return formation

# calculates the maximum distance after mapping
def max_distance_calculator(foramtion1, formation2, order):
    distances = np.zeros(len(foramtion1))
    for i in range(len(foramtion1)):
        distances[i] = euclidean_cost(foramtion1[i], formation2[order[i]])
    return distances.max()
# calculates maximum duration for each mapping 
def max_duration_calculator(foramtion1, formation2, order, max_accel, max_speed):
    distance = max_distance_calculator(foramtion1, formation2, order)
    t = math.sqrt(distance/max_accel)
    t_reach_max = max_accel/max_speed
    if t < t_reach_max:
        return 2*t
    else:
        return 2*t_reach_max + (distance - max_accel*(t_reach_max**2))/max_speed
