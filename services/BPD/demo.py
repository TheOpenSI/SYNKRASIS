import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from services.BPD.bpd import BPD

FUNCTIONAL = """
class Solution:
    def biggest(self, nums: list) -> int:
        best = 0
        for n in nums:
            if n > best:
                best = n
        return best
"""

STDIN = """
n = int(input())
total = 0
for i in range(1, n + 1):
    if i % 3 == 0:
        total += i
print(total)
"""

stdin_factorial = """
n = int(input())
def factorial(x):
    if x == 0:
        return 1
    return x * factorial(x - 1)
print(factorial(n))
"""

# Lines that run but leave no row in the trace: bare return/continue/break/pass, a call that returns None,
# a bare expression, assert, del, try/except/finally, a lambda assignment, `else:` of a while loop.
DROPPED = """
class Solution:
    def scan(self, nums: list) -> int:
        total = 0
        seen = set()
        fn = lambda a: a
        for n in nums:
            if n < 0:
                continue
            self.log(n)
            n
            assert n >= 0
            y = n
            del y
            try:
                z = 10 // n
            except ZeroDivisionError:
                pass
            finally:
                seen.add(n)
            total += n
            if total > 100:
                break
        while total > 0:
            total -= 50
        else:
            total = 5
        return total

    def log(self, x):
        pass
"""

DROPPED_BARE_RETURN = """
class Solution:
    def check(self, x: int) -> None:
        if x > 0:
            return
        print(x)
"""

bpd = BPD()
# print(bpd.trace(FUNCTIONAL, "[1, 2, 3]", entry_point="biggest", expected="-2"))
# print()
# print(bpd.trace(STDIN, "10", expected="20"))
# print()
# print(bpd.trace(stdin_factorial, "5", expected="120"))
print()
print(bpd.trace(DROPPED, "[3, -1, 0, 2]", entry_point="scan"))
print()
print(bpd.trace(DROPPED_BARE_RETURN, "5", entry_point="check"))
print()
