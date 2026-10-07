import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from services.BPD2.bpd2 import CompactDebugger
from services.BPD2.compact_report import CompactConfig
from services.BPD2.fast_tracer import TraceLimit


def trace(source: str, function: str, *args, expected=None, config=None) -> str:
    return CompactDebugger().run(source, function, *args).text(expected=expected, config=config)


class CompactTraceTests(unittest.TestCase):

    def test_loop_values_are_sequences_on_the_loop_and_body_lines(self):
        text = trace("def f(nums):\n    total = 0\n    for n in nums:\n        total += n\n    return total\n",
                     "f", [1, 2, 3, 4])
        self.assertIn("for n in nums:  # 4 iterations; n=1..4", text)
        self.assertIn("total += n  # total=1,3,6,10", text)
        self.assertNotIn("total = 0", text)                       # a literal assignment tells nothing

    def test_unchanged_assigned_values_are_recorded_every_time(self):
        text = trace("def f(xs):\n    for x in xs:\n        y = x // 2\n    return y\n", "f", [2, 3, 2, 3])
        self.assertIn("y=1×4", text)                              # y does not change, but it was assigned 4 times

    def test_branch_outcomes_and_rows_that_ran_in_some_iterations_only(self):
        source = "def f(nums):\n    c = 0\n    for n in nums:\n        if n % 2 == 0:\n            c += 1\n    return c\n"
        text = trace(source, "f", [1, 2, 3, 4])
        self.assertIn("if n % 2 == 0:  # F,T,F,T", text)
        self.assertIn("c += 1  # c=1,2  (iters 2,4)", text)

    def test_a_row_that_skipped_one_iteration_is_marked(self):
        source = "def f(xs):\n    t = 0\n    for x in xs:\n        if x < 0:\n            continue\n        t += x\n    return t\n"
        text = trace(source, "f", [1, 2, -1, 4, 5, 6])
        self.assertIn("(not in iters 3)", text)
        self.assertIn("if x < 0:  # F,F,T,F×3", text)             # the position of the odd one out stays visible

    def test_else_body_is_marked_with_an_else_line(self):
        source = "def f(x):\n    if x > 0:\n        y = 1\n    else:\n        y = x * 2\n    return y\n"
        text = trace(source, "f", -3)
        self.assertIn("if x > 0:  # False", text)
        lines = text.splitlines()
        self.assertEqual(lines[lines.index("  else:") + 1], "    y = x * 2  # y=-6")      # the else body sits under `else:`

    def test_list_updates_are_deltas(self):
        source = "def f(n):\n    out = []\n    sq = [0] * n\n    for i in range(n):\n        sq[i] = i * i\n        out.append(i)\n    return out\n"
        text = trace(source, "f", 4)
        self.assertIn("sq[1..3]=1,4,9", text)                     # sq[0] stays 0: no change, same value
        self.assertIn("out += 0..3", text)

    def test_exception_is_shown_where_it_happened_and_once_at_the_end(self):
        text = trace("def f(items):\n    i = 0\n    while i <= len(items):\n        i += 1\n    return items[i]\n", "f", [10, 20, 30])
        self.assertIn("return items[i]  # raised IndexError", text)
        self.assertTrue(text.splitlines()[-1].startswith("raised IndexError; locals:"))
        self.assertIn("i=4", text.splitlines()[-1])

    def test_expected_value_is_added_to_the_last_line(self):
        text = trace("def f(x):\n    return x + 1\n", "f", 1, expected="3")
        self.assertEqual(text.splitlines()[-1], "returned 2   (expected '3')")

    def test_name_used_in_a_comprehension_is_still_visible_as_a_variable(self):
        source = "def f(xs):\n    col = xs[0]\n    m = min(len(col) for col in xs)\n    return m\n"
        self.assertIn("col=[1, 2]", trace(source, "f", [[1, 2], [3]]))

    def test_calls_with_nothing_to_say_are_not_repeated(self):
        source = "def is_even(x):\n    return x % 2 == 0\n\ndef f(nums):\n    c = 0\n    for n in nums:\n        if is_even(n):\n            c += 1\n    return c\n"
        text = trace(source, "f", [1, 2, 3, 4])
        self.assertNotIn("is_even", text.split("if is_even(n):")[1].split("\n")[0])   # the outcome F,T,F,T says it

    def test_long_pass_through_arguments_are_not_repeated_in_nested_calls(self):
        source = ("def walk(data, i):\n    if i == 0:\n        return 0\n    return walk(data, i - 1) + data[i]\n\n"
                  "def f(data):\n    return walk(data, 2)\n")
        text = trace(source, "f", list(range(100, 160)))
        self.assertEqual(text.count("data=["), 1)                  # in the first header only, shortened

    def test_budget_keeps_the_trace_under_max_chars(self):
        source = "def f(n):\n    t = 0\n    for i in range(n):\n        for j in range(n):\n            t += (i * j) % 7\n    return t\n"
        text = trace(source, "f", 30, config=CompactConfig(max_chars=500))
        self.assertLessEqual(len(text), 600)
        self.assertTrue(text.splitlines()[-1].startswith("returned"))

    def test_trace_limit_stops_a_long_run(self):
        debugger = CompactDebugger(max_steps=200)
        with self.assertRaises(TraceLimit):
            debugger.run("def f():\n    while True:\n        pass\n", "f")


if __name__ == "__main__":
    unittest.main()
