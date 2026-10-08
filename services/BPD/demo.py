# See what BPD returns. No dataset, no LLM:   python services/BPD/demo.py
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from services.BPD.bpd import BPD

# A LeetCode style solution (class Solution). test_input has one json value per line = the arguments.
FUNCTIONAL = """class Solution:
    def biggest(self, nums: list) -> int:
        best = 0
        for n in nums:
            if n > best:
                best = n
        return best
"""

# A stdin program. test_input is what the program reads.
STDIN = """n = int(input())
total = 0
for i in range(1, n + 1):
    if i % 3 == 0:
        total += i
print(total)
"""

bpd = BPD()
print(bpd.trace(FUNCTIONAL, "[-5, -2, -9]", entry_point="biggest", expected="-2"))
print()
print(bpd.trace(STDIN, "10", expected="20"))
