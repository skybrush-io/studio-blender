#formation_mapping
import numpy as np
from scipy.optimize import linear_sum_assignment as lsa
#cost function that should be used to create cost matrix
def square_euclidean_cost(coord1, coord2):
    return (coord1[0]-coord2[0])**2 + (coord1[1]-coord2[1])**2 + (coord1[2]-coord2[2])**2

def euclidean_cost(coord1, coord2):
    return ((coord1[0]-coord2[0])**2 + (coord1[1]-coord2[1])**2 + (coord1[2]-coord2[2])**2)**0.5

#function that calculates cost matrix
def cost_matrix_calc(formation1, formation2, costFunction):
    n = formation1.shape[0]
    cost_matrix = np.zeros((n,n))
    for coordIndex1, coord1 in enumerate(formation1):
        for coordIndex2, coord2 in enumerate(formation2):
            cost_matrix[coordIndex1][coordIndex2] = costFunction(coord1, coord2)
    return cost_matrix  

#function that provides optimum mapping with respect to cost function
def smart_transition_mapper(formation1, formation2, costFunction):
    cost_matrix = cost_matrix_calc(formation1, formation2, costFunction)
    row_ind, col_ind = lsa(cost_matrix)
    mapping_order = col_ind
    min_cost = cost_matrix[row_ind, col_ind].sum()
    return mapping_order, min_cost

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


ground_formation = create_grid_formation(4, 4, 0, 3)
stage1 = create_grid_formation(2, 2, 1, 3)
stage2 = create_grid_formation(2, 2, 2, 3)
stage3 = create_grid_formation(2, 2, 3, 3)
stage4 = create_grid_formation(2, 2, 4, 3)

air_formation = np.append(stage1, stage2, axis=0)
air_formation = np.append(air_formation ,stage3, axis=0)
air_formation = np.append(air_formation ,stage4, axis=0)

order, cost = smart_transition_mapper(ground_formation, air_formation, square_euclidean_cost)
print(ground_formation)
print(air_formation)
print(order)
# for idx, item in enumerate(order):
#     print(ground_formation[idx], "goes to", air_formation[item])


