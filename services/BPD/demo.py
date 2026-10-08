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

bpd = BPD()
print(bpd.trace(FUNCTIONAL, "[1, 2, 3]", entry_point="biggest", expected="-2"))
print()
print(bpd.trace(STDIN, "10", expected="20"))
