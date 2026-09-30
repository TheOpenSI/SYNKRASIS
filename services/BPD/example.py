import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from services.BPD.bpd import BreakpointDebugger
from services.BPD.tests import test_functions

SAMPLE = '''
def double(x):
    return x * 2

def sum_list(nums):
    total = 0
    for n in nums:
        total += double(n)
    return total

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def divide(a, b):
    return a / b

def sum_of_divisions(nums):
    total = 0
    for n in nums:
        total += divide(10, n)
    return total

class Counter:
    def __init__(self, start):
        self.count = start

    def bump_until(self, limit):
        steps = 0
        while self.count < limit:
            self.count += 2
            steps += 1
            if steps > 100:
                break
        return steps
'''


def main() -> None:
    debugger = BreakpointDebugger()
    print(debugger.run(SAMPLE, "sum_list", [1, 2, 3, 4]))
    print(debugger.run(SAMPLE, "factorial", 4))
    print(debugger.run(SAMPLE, "sum_of_divisions", [5, 2, 0, 1]))
    print(debugger.run_expression(SAMPLE, "Counter(1).bump_until(6)"))
    print(debugger.run_callable(test_functions.recursive_with_loop, 3))


if __name__ == "__main__":
    main()
