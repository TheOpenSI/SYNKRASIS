import numpy as np
def multiply_matrices(A, B):
    return np.dot(A, B)

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
C = multiply_matrices(A, B)
print(C)