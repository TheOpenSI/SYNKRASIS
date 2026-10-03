# n = int(input())
# result = 1
# for i in range(2, n + 1):
#     result *= i
# print(result)

class Solution:
    def factorial(self, n: int) -> int:
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result