# =============================================================================================
# The simplest way to see what BPD does. No dataset, no LLM, no PyCapsule.
#
#   python services/BPD/simple_demo.py
#
# Each case is: some code (what an LLM might write), a function name, the arguments of ONE test,
# and the answer the test expects. BreakpointDebugger.run() executes the function while recording
# every line that runs, then prints the story of that run.
#
# How to read a trace:
#   Line 7 `total += n`: total: 0 -> 3      line 7 ran, and variable total changed from 0 to 3
#   Line 12 `if x > 0:` was True (x = 5)     an `if` and which way it went
#   `for ...` ran 4 iterations               a loop, followed by what happened in each iteration
#   called double(x=2) -> 4                  a call to another function and what it returned
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from services.BPD.bpd import BreakpointDebugger
from services.BPD.report import ReportConfig

# (title, code, function to call, arguments, expected answer)
CASES = [
    ("1. Correct code: sum of a list",
     """
def sum_list(nums):
    total = 0
    for n in nums:
        total += n
    return total
""", "sum_list", ([1, 2, 3],), 6),

    ("2. Wrong answer: biggest number of a list (breaks when every number is negative)",
     """
def biggest(nums):
    best = 0
    for n in nums:
        if n > best:
            best = n
    return best
""", "biggest", ([-5, -2, -9],), -2),

    ("3. A function calling itself: factorial",
     """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
""", "factorial", (4,), 24),

    ("4. A crash: reads one position too far",
     """
def last_item(items):
    i = 0
    while i <= len(items):
        i += 1
    return items[i]
""", "last_item", ([10, 20, 30],), 30),

    ("5. A helper function being called inside a loop",
     """
def is_even(x):
    return x % 2 == 0

def count_even(nums):
    count = 0
    for n in nums:
        if is_even(n):
            count += 1
    return count
""", "count_even", ([1, 2, 3, 4],), 2),
]


def run_case(title: str, code: str, function: str, args: tuple, expected) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)

    # include_source=True prints the code with line numbers first, so "Line 7" can be looked up.
    debugger = BreakpointDebugger(ReportConfig(include_source=True))
    report = debugger.run(code, function, *args)

    print(report.text)
    # report.result is what the function returned, report.exception is what it raised (or None)
    if report.exception is not None:
        verdict = f"CRASHED with {type(report.exception).__name__}"
    elif report.result == expected:
        verdict = "PASS"
    else:
        verdict = f"FAIL (expected {expected!r})"
    call = f"{function}({', '.join(repr(a) for a in args)})"
    print(f"Test {call}: got {report.result!r} -> {verdict}")


def main() -> None:
    for case in CASES:
        run_case(*case)


if __name__ == "__main__":
    main()
