import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from services.BPD.bpd import BreakpointDebugger
from services.BPD.report import ReportConfig
from services.BPD.tests import test_functions

SOURCE = '''
counter = 0

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

def find_first_even(nums):
    for n in nums:
        if n % 2 == 0:
            return n
    return None

def count_up(limit):
    i = 0
    while True:
        i += 1
        if i >= limit:
            break
    return i

def grid_sum(rows):
    total = 0
    for row in rows:
        for cell in row:
            total += cell
    return total

def bump_counter(times):
    global counter
    for _ in range(times):
        counter += 1
    return counter

def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None

def evens(n):
    for i in range(n):
        if i % 2 == 0:
            yield i

def sum_evens(n):
    return sum(evens(n))

def doubled_all(nums):
    return [double(x) for x in nums]

def sign(x):
    if x > 0: return 1
    return -1

def classify(x):
    if x < 0:
        kind = "negative"
    elif x == 0:
        kind = "zero"
    else:
        kind = "positive"
    return kind

class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)
        return len(self.items)

    def push_many(self, items):
        for item in items:
            self.push(item)
        return self.items
'''


class BreakpointDebuggerTests(unittest.TestCase):

    def setUp(self):
        self.debugger = BreakpointDebugger()

    def report(self, entry, *args, **kwargs):
        return self.debugger.run(SOURCE, entry, *args, **kwargs)

    # -- basics ----------------------------------------------------------------

    def test_loop_iterations_and_accumulator(self):
        report = self.report("sum_list", [1, 2, 3, 4])
        self.assertEqual(report.result, 20)
        self.assertIsNone(report.exception)
        text = report.text
        self.assertIn("Outcome: returned 20", text)
        self.assertIn("`for n in nums:` (nums = [1, 2, 3, 4]) ran 4 iterations", text)
        self.assertIn("Iteration 1 (n = 1): line 10 `total += double(n)`: called double(x=1) -> 2; total: 0 -> 2", text)
        self.assertIn("Iteration 4 (n = 4): line 10 `total += double(n)`: called double(x=4) -> 8; total: 12 -> 20", text)
        self.assertIn("After the loop: total = 20", text)
        self.assertIn("Line 11 `return total`: sum_list returned 20", text)

    def test_source_listing_included_by_default(self):
        text = self.report("double", 3).text
        self.assertIn("Source (line numbers below refer to this listing):", text)
        self.assertIn(" 4 | def double(x):", text)
        without = BreakpointDebugger(ReportConfig(include_source=False)).run(SOURCE, "double", 3).text
        self.assertNotIn("Source (", without)

    def test_recursion_is_nested_with_branch_outcomes(self):
        text = self.report("factorial", 3).text
        self.assertIn("Call factorial(n=3)", text)
        self.assertIn("Line 14 `if n <= 1:` was False (n = 3)", text)
        self.assertIn("called factorial(n=2):", text)
        self.assertIn("called factorial(n=1):", text)
        self.assertIn("Line 14 `if n <= 1:` was True (n = 1)", text)
        self.assertIn("Line 15 `return 1`: factorial returned 1", text)
        self.assertIn("factorial returned 6", text)
        # deeper calls are indented further than their callers
        outer = next(l for l in text.splitlines() if "called factorial(n=2):" in l)
        inner = next(l for l in text.splitlines() if "called factorial(n=1):" in l)
        self.assertLess(len(outer) - len(outer.lstrip()), len(inner) - len(inner.lstrip()))

    def test_structured_invocations_are_available(self):
        report = self.report("factorial", 3)
        root = report.invocations[0]
        self.assertEqual(root.name, "factorial")
        self.assertEqual(root.args, {"n": "3"})
        self.assertEqual(root.return_value, "6")
        self.assertEqual(root.children[0].children[0].args, {"n": "1"})

    # -- exceptions ------------------------------------------------------------

    def test_exception_propagation_shows_state_at_failure(self):
        report = self.report("sum_of_divisions", [5, 0, 1])
        self.assertIsInstance(report.exception, ZeroDivisionError)
        text = report.text
        self.assertIn("Outcome: raised ZeroDivisionError: division by zero", text)
        self.assertIn("ran 2 iterations, then an exception left the loop", text)
        self.assertIn("Line 19 `return a / b`: raised ZeroDivisionError: division by zero", text)
        self.assertIn("propagated out of divide (state: a = 10, b = 0)", text)
        self.assertIn("propagated out of sum_of_divisions (state: nums = [5, 0, 1], total = 2.0, n = 0)", text)

    def test_handled_exception_does_not_propagate(self):
        report = self.report("safe_divide", 1, 0)
        self.assertIsNone(report.exception)
        text = report.text
        self.assertIn("raised ZeroDivisionError: division by zero", text)
        self.assertNotIn("propagated out of", text)
        self.assertIn("safe_divide returned None", text)

    # -- loops -----------------------------------------------------------------

    def test_return_from_inside_loop(self):
        text = self.report("find_first_even", [1, 3, 4, 5]).text
        self.assertIn("ran 3 iterations, then returned from inside the loop", text)
        self.assertIn("`if n % 2 == 0:` was True (n = 4); line 30 `return n`: find_first_even returned 4", text)
        self.assertIn("find_first_even returned 4", text)
        self.assertNotIn("After the loop", text)

    def test_while_true_with_break(self):
        text = self.report("count_up", 3).text
        self.assertIn("`while True:` ran 3 iterations, then exited via break", text)
        self.assertIn("`if i >= limit:` was True (i = 3, limit = 3)", text)
        self.assertIn("After the loop: i = 3", text)

    def test_nested_loops(self):
        text = self.report("grid_sum", [[1, 2], [3]]).text
        self.assertIn("`for row in rows:` (rows = [[1, 2], [3]]) ran 2 iterations", text)
        self.assertIn("Iteration 1 (row = [1, 2]):", text)
        self.assertIn("`for cell in row:` (row = [1, 2]) ran 2 iterations", text)
        self.assertIn("Iteration 1 (cell = 1): line 45 `total += cell`: total: 0 -> 1", text)
        self.assertIn("`for cell in row:` (row = [3]) ran 1 iteration", text)
        self.assertIn("After the loop: total = 6\n", text)
        self.assertNotIn("cell = 3\n", text)
        self.assertIn("grid_sum returned 6", text)

    def test_empty_loop(self):
        text = self.report("sum_list", []).text
        self.assertIn("ran 0 iterations (body never executed)", text)
        self.assertIn("sum_list returned 0", text)

    def test_long_loops_are_elided(self):
        debugger = BreakpointDebugger(ReportConfig(max_iterations_shown=5, iterations_tail=2))
        text = debugger.run(SOURCE, "sum_list", list(range(1, 21))).text
        self.assertIn("ran 20 iterations", text)
        self.assertIn("Iteration 3 (n = 3)", text)
        self.assertNotIn("Iteration 4 (n = 4)", text)
        self.assertIn("... 15 iterations omitted ...", text)
        self.assertIn("Iteration 19 (n = 19)", text)
        self.assertIn("Iteration 20 (n = 20)", text)

    # -- branches --------------------------------------------------------------

    def test_elif_chain(self):
        text = self.report("classify", 0).text
        self.assertIn("Line 76 `if x < 0:` was False (x = 0)", text)
        self.assertIn("Line 78 `elif x == 0:` was True (x = 0)", text)
        self.assertIn("Line 79 `kind = \"zero\"`: kind = 'zero'", text)
        self.assertNotIn("Line 81", text)

    def test_single_line_if_body(self):
        self.assertIn("Line 72 `if x > 0: return 1` was True (x = 5): sign returned 1", self.report("sign", 5).text)
        negative = self.report("sign", -5).text
        self.assertIn("Line 72 `if x > 0: return 1` was False (x = -5)", negative)
        self.assertIn("Line 73 `return -1`: sign returned -1", negative)
        self.assertNotIn("End of function reached", negative)

    # -- globals, classes, generators, comprehensions ---------------------------

    def test_global_variable_changes_are_tracked(self):
        text = self.report("bump_counter", 2).text
        self.assertIn("Iteration 1 (_ = 0): line 51 `counter += 1`: counter (global): 0 -> 1", text)
        self.assertIn("After the loop: counter (global) = 2", text)

    def test_method_calls_show_object_state(self):
        report = self.debugger.run_expression(SOURCE, "Stack().push_many(['a', 'b'])")
        self.assertEqual(report.result, ["a", "b"])
        text = report.text
        self.assertIn("Call __init__(self=Stack())  [Stack.__init__", text)
        self.assertIn("Call push_many(self=Stack(items=[]), items=['a', 'b'])  [Stack.push_many", text)
        self.assertIn("called push(self=Stack(items=[]), item='a') -> 1; self: Stack(items=[]) -> Stack(items=['a'])", text)
        self.assertIn("After the loop: self = Stack(items=['a', 'b'])", text)

    def test_generator_yields(self):
        text = self.report("sum_evens", 5).text
        self.assertIn("called evens(n=5):", text)
        self.assertIn("`if i % 2 == 0:` was True (i = 0)", text)
        self.assertIn("evens yielded 0, 2, 4", text)
        self.assertIn("sum_evens returned 6", text)

    def test_calls_from_comprehension_are_attributed_to_the_function(self):
        text = self.report("doubled_all", [1, 2]).text
        self.assertIn("called double(x=1) -> 2; called double(x=2) -> 4", text)
        self.assertNotIn("<listcomp>", text)

    def test_many_calls_on_one_line_are_capped(self):
        debugger = BreakpointDebugger(ReportConfig(max_calls_per_step=2))
        text = debugger.run(SOURCE, "doubled_all", [1, 2, 3, 4, 5]).text
        self.assertIn("called double(x=2) -> 4; ... and 3 more calls to double", text)

    def test_call_depth_limit(self):
        debugger = BreakpointDebugger(ReportConfig(max_call_depth=1))
        text = debugger.run(SOURCE, "factorial", 4).text
        self.assertIn("called factorial(n=3):", text)
        self.assertIn("called factorial(n=2) -> 2 (nested details omitted: depth limit)", text)

    # -- entry points ----------------------------------------------------------

    def test_run_callable_traces_the_functions_file(self):
        report = self.debugger.run_callable(test_functions.sum_list, [1, 2])
        self.assertEqual(report.result, 6)
        text = report.text
        self.assertIn("Execution report for `sum_list([1, 2])`", text)
        self.assertIn("def sum_list(nums: list[int]) -> int:", text)
        self.assertIn("called double(x=1) -> 2", text)

    def test_run_callable_with_exception(self):
        report = self.debugger.run_callable(test_functions.sum_list_with_exception, [1, 0])
        self.assertIsInstance(report.exception, ZeroDivisionError)
        self.assertIn("propagated out of divide", report.text)

    def test_unknown_entry_point(self):
        with self.assertRaises(NameError):
            self.report("missing")

    def test_expression_without_traced_calls(self):
        report = self.debugger.run_expression(SOURCE, "1 + 1")
        self.assertEqual(report.result, 2)
        self.assertIn("No traced function was called.", report.text)

    def test_report_str_is_text(self):
        report = self.report("double", 2)
        self.assertEqual(str(report), report.text)


if __name__ == "__main__":
    unittest.main()
