def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def double(x: int) -> int:
    return x * 2


def sum_list(nums: list[int]) -> int:
    total = 0
    for n in nums:
        total += double(n)
    return total


def divide(a: int, b: int) -> float:
    return a / b


def sum_list_with_exception(nums: list[int]) -> int:
    total = 0
    for n in nums:
        total += divide(10, n)
    return total


def recursive_with_loop(n: int) -> int:
    total = 0
    for i in range(n):
        total += i
    if n <= 1:
        return total
    return total + recursive_with_loop(n - 1)
