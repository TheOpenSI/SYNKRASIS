import os
import subprocess
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from services.BPD.bpd import BPD


def trace(source: str, call: str, expected=None, **limits) -> str:
    """Trace the expression `call` (e.g. "f([1, 2])") in the namespace of source."""
    return BPD(**limits).trace_expression(source, call, expected)


class FormatTests(unittest.TestCase):

    def test_loop_values_are_sequences_on_the_loop_and_body_lines(self):
        text = trace("def f(nums):\n    total = 0\n    for n in nums:\n        total += n\n    return total\n", "f([1, 2, 3, 4])")
        self.assertIn("for n in nums:  # 4 iterations; n=1..4", text)
        self.assertIn("total += n  # total=1,3,6,10", text)
        self.assertNotIn("total = 0", text)                       # a literal assignment tells nothing

    def test_unchanged_assigned_values_are_recorded_every_time(self):
        text = trace("def f(xs):\n    for x in xs:\n        y = x // 2\n    return y\n", "f([2, 3, 2, 3])")
        self.assertIn("y=1×4", text)                              # y does not change, but it was assigned 4 times

    def test_branch_outcomes_and_rows_that_ran_in_some_iterations_only(self):
        source = "def f(nums):\n    c = 0\n    for n in nums:\n        if n % 2 == 0:\n            c += 1\n    return c\n"
        text = trace(source, "f([1, 2, 3, 4])")
        self.assertIn("if n % 2 == 0:  # F,T,F,T", text)
        self.assertIn("c += 1  # c=1,2  (iters 2,4)", text)

    def test_a_row_that_skipped_one_iteration_is_marked(self):
        source = "def f(xs):\n    t = 0\n    for x in xs:\n        if x < 0:\n            continue\n        t += x\n    return t\n"
        text = trace(source, "f([1, 2, -1, 4, 5, 6])")
        self.assertIn("(not in iters 3)", text)
        self.assertIn("if x < 0:  # F,F,T,F×3", text)             # the position of the odd one out stays visible

    def test_else_body_is_marked_with_an_else_line(self):
        source = "def f(x):\n    if x > 0:\n        y = 1\n    else:\n        y = x * 2\n    return y\n"
        lines = trace(source, "f(-3)").splitlines()
        self.assertIn("if x > 0:  # False", "\n".join(lines))
        self.assertEqual(lines[lines.index("  else:") + 1], "    y = x * 2  # y=-6")

    def test_list_updates_are_deltas(self):
        source = "def f(n):\n    out = []\n    sq = [0] * n\n    for i in range(n):\n        sq[i] = i * i\n        out.append(i)\n    return out\n"
        text = trace(source, "f(4)")
        self.assertIn("sq[0..3]=0,1,4,9", text)                   # slots and values, also the 0 that left sq unchanged
        self.assertIn("out += 0..3", text)                        # append: shown as what was added

    def test_a_write_that_changes_nothing_is_still_shown(self):
        source = "def f(n):\n    G = [[0] * n for _ in range(n)]\n    for i in range(n):\n        for j in range(n):\n            G[i][j] = (i - i) * j\n    return G\n"
        self.assertIn("G[0][0]..G[1][1]=0×4", trace(source, "f(2)"))      # ran 4 times and wrote 0: the list never changed

    def test_nested_list_writes_show_the_value_not_the_whole_row(self):
        source = "def f(n):\n    A = [[0] * n for _ in range(n)]\n    for i in range(n):\n        for j in range(n):\n            A[i][j] = i * 10 + j\n    return A\n"
        text = trace(source, "f(2)")
        self.assertIn("A[0][0]=0,A[0][1]=1,A[1][0]=10,A[1][1]=11", text)
        self.assertNotIn("[0, 1],[", text)                        # no dump of whole rows

    def test_attribute_writes_show_the_value_written(self):
        source = "class C:\n    def __init__(self):\n        self.count = 0\n    def bump(self, times):\n        for _ in range(times):\n            self.count += 2\n        return self.count\n"
        self.assertIn("self.count=2,4,6", trace(source, "C().bump(3)"))

    def test_swap_shows_both_targets(self):
        source = "def f(a):\n    i, j = 0, 2\n    a[i], a[j] = a[j], a[i]\n    return a\n"
        self.assertIn("a[0]=3; a[2]=1", trace(source, "f([1, 2, 3])"))

    def test_the_slot_is_shown_even_when_the_index_is_computed_on_the_line(self):
        source = "def f(n):\n    a = [0] * 5\n    for i in range(n):\n        a[(i * 3) % 5] = i + 1\n    return a\n"
        self.assertIn("a[0]=1,a[3]=2,a[1]=3", trace(source, "f(3)"))       # slots 0, 3, 1: nothing else says which

    def test_dictionary_keys_are_the_slots(self):
        source = "def f(words):\n    d = {}\n    for w in words:\n        d[w] = len(w)\n    return d\n"
        self.assertIn("d['aa']=2,d['b']=1", trace(source, "f(['aa', 'b'])"))

    def test_a_target_with_a_call_is_never_evaluated(self):
        source = "calls = []\ndef pick():\n    calls.append(1)\n    return 0\n\ndef f(a):\n    a[pick()] = 5\n    return len(calls)\n"
        self.assertEqual(trace(source, "f([0, 0])").splitlines()[-1], "returned 1")   # pick() ran once, not twice

    def test_exception_is_shown_where_it_happened_and_once_at_the_end(self):
        text = trace("def f(items):\n    i = 0\n    while i <= len(items):\n        i += 1\n    return items[i]\n", "f([10, 20, 30])")
        self.assertIn("return items[i]  # raised IndexError", text)
        self.assertTrue(text.splitlines()[-1].startswith("raised IndexError; locals:"))
        self.assertIn("i=4", text.splitlines()[-1])

    def test_expected_value_is_added_to_the_last_line(self):
        self.assertEqual(trace("def f(x):\n    return x + 1\n", "f(1)", expected="3").splitlines()[-1], "returned 2   (expected '3')")

    def test_name_used_in_a_comprehension_is_still_visible_as_a_variable(self):
        source = "def f(xs):\n    col = xs[0]\n    m = min(len(col) for col in xs)\n    return m\n"
        self.assertIn("col=[1, 2]", trace(source, "f([[1, 2], [3]])"))

    def test_calls_with_nothing_to_say_are_not_repeated(self):
        source = "def is_even(x):\n    return x % 2 == 0\n\ndef f(nums):\n    c = 0\n    for n in nums:\n        if is_even(n):\n            c += 1\n    return c\n"
        text = trace(source, "f([1, 2, 3, 4])")
        self.assertNotIn("is_even", text.split("if is_even(n):")[1].split("\n")[0])   # the outcome F,T,F,T says it

    def test_long_pass_through_arguments_are_not_repeated_in_nested_calls(self):
        source = ("def walk(data, i):\n    if i == 0:\n        return 0\n    return walk(data, i - 1) + data[i]\n\n"
                  "def f(data):\n    return walk(data, 2)\n")
        self.assertEqual(trace(source, f"f({list(range(100, 160))})").count("data=["), 1)

    def test_size_budget_is_respected(self):
        source = "def f(n):\n    t = 0\n    for i in range(n):\n        for j in range(n):\n            t += (i * j) % 7\n    return t\n"
        text = trace(source, "f(30)", max_chars=500)
        self.assertLessEqual(len(text), 600)
        self.assertTrue(text.splitlines()[-1].startswith("returned"))

    def test_huge_list_does_not_slow_the_trace_down(self):
        text = trace("def f(n):\n    a = [0] * n\n    for i in range(5):\n        a[i] = i\n    return len(a)\n", "f(3000000)")
        self.assertIn("(len=3000000)", text)


class TraceTests(unittest.TestCase):
    """The way LiveCodeBench uses it: code + the input of one test."""

    FUNCTIONAL = "class Solution:\n    def total(self, nums: list, k: int) -> int:\n        s = 0\n        for n in nums:\n            s += n * k\n        return s\n"
    STDIN = "n = int(input())\ntotal = 0\nfor i in range(n):\n    total += i\nprint(total)\n"

    def test_functional_arguments_are_one_json_value_per_line(self):
        text = BPD().trace_in_process(self.FUNCTIONAL, "[1, 2, 3]\n2", entry_point="total", expected="12")
        self.assertIn("total(nums=[1, 2, 3], k=2):", text)
        self.assertIn("s += n * k  # s=2,6,12", text)
        self.assertEqual(text.splitlines()[-1], "returned 12   (expected '12')")

    def test_stdin_program_is_traced_and_its_output_reported(self):
        text = BPD().trace_in_process(self.STDIN, "4", expected="7")
        self.assertIn("for i in range(n):  # 4 iterations; i=0..3", text)
        self.assertEqual(text.splitlines()[-1], "printed '6'   (expected '7')")

    def test_stdin_program_with_main_function_and_guard(self):
        code = "import sys\ndef solve():\n    n = int(sys.stdin.readline())\n    print(n * 2)\n\nif __name__ == '__main__':\n    solve()\n"
        text = BPD().trace_in_process(code, "21\n")
        self.assertIn("n = int(sys.stdin.readline())  # n=21", text)
        self.assertEqual(text.splitlines()[-1], "printed '42'")

    def test_a_crash_in_the_solution_is_a_trace_not_a_failure(self):
        text = BPD().trace_in_process("n = int(input())\nprint(1 // n)\n", "0")
        self.assertIn("raised ZeroDivisionError", text.splitlines()[-1])

    def test_syntax_error_gives_none_and_a_reason(self):
        bpd = BPD()
        self.assertIsNone(bpd.trace_in_process("def f(:\n", "1"))
        self.assertIn("SyntaxError", bpd.last_error)

    def test_isolated_trace_matches_the_in_process_trace(self):
        bpd = BPD()
        self.assertEqual(bpd.trace(self.STDIN, "4", expected="7"), bpd.trace_in_process(self.STDIN, "4", expected="7"))

    def test_a_hanging_solution_does_not_hang_the_caller(self):
        bpd = BPD(timeout=4)
        self.assertIsNone(bpd.trace("x = sum(range(10**10))\nprint(x)\n", ""))          # one long native call, no line events
        self.assertEqual(bpd.last_error, "timeout")

    def test_an_endless_loop_hits_the_trace_limit(self):
        bpd = BPD(max_steps=500)
        self.assertIsNone(bpd.trace("while True:\n    pass\n", ""))
        self.assertEqual(bpd.last_error, "trace_limit")

    def test_sys_exit_and_memory_bomb_are_contained(self):
        bpd = BPD()
        self.assertIsNone(bpd.trace("import sys\nsys.exit(3)\n", ""))
        self.assertIn("SystemExit", bpd.last_error)
        text = bpd.trace("a = [0] * (10**11)\nprint(len(a))\n", "")
        self.assertTrue(text is None or "MemoryError" in text)


def docker_image_available(image: str = "synkrasis") -> bool:
    try:
        return subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


@unittest.skipUnless(docker_image_available(), "docker image 'synkrasis' is not available")
class SandboxTests(unittest.TestCase):
    """trace() in a throwaway container: same result as on the host, but the code cannot reach the network or hang us."""
    STDIN = "n = int(input())\ntotal = 0\nfor i in range(1, n + 1):\n    if i % 3 == 0:\n        total += i\nprint(total)\n"

    def test_same_trace_as_on_the_host(self):
        self.assertEqual(BPD(sandbox_image="synkrasis").trace(self.STDIN, "10", expected="20"),
                         BPD().trace(self.STDIN, "10", expected="20"))

    def test_traced_code_has_no_network(self):
        code = "import socket\ntry:\n    socket.create_connection(('1.1.1.1', 80), timeout=3)\n    print('open')\nexcept OSError:\n    print('blocked')\n"
        self.assertIn("printed 'blocked'", BPD(sandbox_image="synkrasis").trace(code, ""))

    def test_a_hang_is_killed_and_its_container_removed(self):
        bpd = BPD(sandbox_image="synkrasis", timeout=4)
        self.assertIsNone(bpd.trace("x = sum(range(10**10))\nprint(x)\n", ""))
        self.assertEqual(bpd.last_error, "timeout")
        left = subprocess.run("docker ps -a --format '{{.Names}}' | grep -c '^bpd_'", shell=True, capture_output=True, text=True)
        self.assertEqual(left.stdout.strip(), "0")


if __name__ == "__main__":
    unittest.main()
