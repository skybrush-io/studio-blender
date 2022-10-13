from turtle import distance
import numpy as np
# import sys
# sys.path.insert(0,"/home/sahar/.local/lib/python3.10/site-packages")
# from scipy.optimize import linear_sum_assignment as lsa
#from scipy.optimize import linear_sum_assignment as lsa
import math
from ServerRequest import ask_skyc_server
def min_zero_row(zero_mat, mark_zero):
    '''
    The function can be splitted into two steps:
    # 1 The function is used to find the row which containing the fewest 0.
    # 2 Select the zero number on the row, and then marked the element corresponding row and column as False
    '''

    # Find the row
    min_row = [99999, -1]

    for row_num in range(zero_mat.shape[0]):
        if np.sum(zero_mat[row_num] == True) > 0 and min_row[0] > np.sum(zero_mat[row_num] == True):
            min_row = [np.sum(zero_mat[row_num] == True), row_num]

    # Marked the specific row and column as False
    zero_index = np.where(zero_mat[min_row[1]] == True)[0][0]
    mark_zero.append((min_row[1], zero_index))
    zero_mat[min_row[1], :] = False
    zero_mat[:, zero_index] = False


def mark_matrix(mat):
    '''
    Finding the returning possible solutions for LAP problem.
    '''

    # Transform the matrix to boolean matrix(0 = True, others = False)
    cur_mat = mat
    zero_bool_mat = (cur_mat == 0)
    zero_bool_mat_copy = zero_bool_mat.copy()

    # Recording possible answer positions by marked_zero
    marked_zero = []
    while (True in zero_bool_mat_copy):
        min_zero_row(zero_bool_mat_copy, marked_zero)

    # Recording the row and column positions seperately.
    marked_zero_row = []
    marked_zero_col = []
    for i in range(len(marked_zero)):
        marked_zero_row.append(marked_zero[i][0])
        marked_zero_col.append(marked_zero[i][1])

    # Step 2-2-1
    non_marked_row = list(set(range(cur_mat.shape[0])) - set(marked_zero_row))

    marked_cols = []
    check_switch = True
    while check_switch:
        check_switch = False
        for i in range(len(non_marked_row)):
            row_array = zero_bool_mat[non_marked_row[i], :]
            for j in range(row_array.shape[0]):
                # Step 2-2-2
                if row_array[j] == True and j not in marked_cols:
                    # Step 2-2-3
                    marked_cols.append(j)
                    check_switch = True

        for row_num, col_num in marked_zero:
            # Step 2-2-4
            if row_num not in non_marked_row and col_num in marked_cols:
                # Step 2-2-5
                non_marked_row.append(row_num)
                check_switch = True
    # Step 2-2-6
    marked_rows = list(set(range(mat.shape[0])) - set(non_marked_row))

    return (marked_zero, marked_rows, marked_cols)


def adjust_matrix(mat, cover_rows, cover_cols):
    cur_mat = mat
    non_zero_element = []

    # Step 4-1
    for row in range(len(cur_mat)):
        if row not in cover_rows:
            for i in range(len(cur_mat[row])):
                if i not in cover_cols:
                    non_zero_element.append(cur_mat[row][i])
    min_num = min(non_zero_element)

    # Step 4-2
    for row in range(len(cur_mat)):
        if row not in cover_rows:
            for i in range(len(cur_mat[row])):
                if i not in cover_cols:
                    cur_mat[row, i] = cur_mat[row, i] - min_num
    # Step 4-3
    for row in range(len(cover_rows)):
        for col in range(len(cover_cols)):
            cur_mat[cover_rows[row], cover_cols[col]
                ] = cur_mat[cover_rows[row], cover_cols[col]] + min_num
    return cur_mat


def hungarian_algorithm(mat):
    dim = mat.shape[0]
    cur_mat = mat

    # Step 1 - Every column and every row subtract its internal minimum
    for row_num in range(mat.shape[0]):
        cur_mat[row_num] = cur_mat[row_num] - np.min(cur_mat[row_num])

    for col_num in range(mat.shape[1]):
        cur_mat[:, col_num] = cur_mat[:, col_num] - np.min(cur_mat[:, col_num])
    zero_count = 0
    while zero_count < dim:
        # Step 2 & 3
        ans_pos, marked_rows, marked_cols = mark_matrix(cur_mat)
        zero_count = len(marked_rows) + len(marked_cols)

        if zero_count < dim:
            cur_mat = adjust_matrix(cur_mat, marked_rows, marked_cols)

    return ans_pos


def ans_calculation(mat, pos):
    total = 0
    ans_mat = np.zeros((mat.shape[0], mat.shape[1]))
    for i in range(len(pos)):
        total += mat[pos[i][0], pos[i][1]]
        ans_mat[pos[i][0], pos[i][1]] = mat[pos[i][0], pos[i][1]]
    return total, ans_mat

def lsa(mat):
    ans_pos = hungarian_algorithm(mat.copy())
    row_ind = []
    col_ind = []
    for i in ans_pos:
        row_ind.append(i[0])
        col_ind.append(i[1])
    return np.transpose(row_ind), np.transpose(col_ind)

class cost_block:
    x = 0
    y = 0
    cost = 0

def getCost(self):
        return self.cost

def hall_condition_check(cost_mat, threshold):
    row_ind, col_ind = lsa(cost_mat)
    min_cost = cost_mat[row_ind, col_ind].sum()
    if min_cost < threshold:
        return True
    else:
        return False

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
    row_ind, col_ind = lsa(cost_matrix)
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
        for item in E0:
            m_copy[item.x][item.y] = 10**5
        if hall_condition_check(m_copy, 10**4) == True:
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
    row_ind, col_ind = lsa(m_copy)
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
"""an example random formation to test"""
ground_formation = np.random.randint(0,100,size=(25,3))
air_formation = np.random.randint(0,100,size=(25,3))

order, cost = smart_transition_mapper(ground_formation, air_formation, square_euclidean_cost)
order2, cost2 = smart_transition_mapper(ground_formation, air_formation, euclidean_cost)
order3, cost3 = optimal_transition_mapper(ground_formation, air_formation)
print(cost)
print(cost2)
print(cost3)

Skyc_order, Skyc_duration = ask_skyc_server(ground_formation, air_formation)
Skyc_cost = max_distance_calculator(ground_formation, air_formation, order)
print(Skyc_cost)
print("Skyc duration:", np.array(Skyc_duration).max())
print("Our duration:", max_duration_calculator(ground_formation,air_formation, order, 3, 5))
