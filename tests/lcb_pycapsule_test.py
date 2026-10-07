# =============================================================================================
# End to end tests of PyCapsule_LiveCodeBench with a scripted (fake) LLM, no API calls.
# Runs real code in a LocalContainer. Needs data/LiveCodeBench/test6.jsonl (not in git).
#   python -m unittest tests.lcb_pycapsule_test
# =============================================================================================
import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import types
import unittest
from collections import deque

try:
    import scipy.optimize  # noqa: F401
except ModuleNotFoundError:   # only DDI needs scipy
    sys.modules["scipy"] = types.ModuleType("scipy")
    sys.modules["scipy.optimize"] = types.ModuleType("scipy.optimize")
    sys.modules["scipy.optimize"].curve_fit = None

from services.LLM.LLMBase import LLMBase
from services.Container.LocalContainer import LocalContainer
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench
from data.LiveCodeBench.LiveCodeBench import LiveCodeBench

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "LiveCodeBench", "test6.jsonl")


def reply(code: str) -> str:
    return f"### Step-by-step reasoning\nx\n\n### Requirements\nNone\n\n### Code\n```python\n{code}\n```"


class FakeLLM(LLMBase):
    def __init__(self, responses: list[str]) -> None:
        super().__init__("fake", enable_chat_history=True)
        self.responses = deque(responses)
        self.prompts: list[str] = []

    def generate_response(self, user_prompt, context=None, suppress_conversation_history=True):
        self.prompts.append(user_prompt)
        return self.responses.popleft()

    def cleanup(self):
        pass


# abc387_b: sum of the 9x9 table without X (stdin). 3708: zigzagTraversal (functional).
TABLE_OK = "x = int(input())\nprint(sum(i*j for i in range(1,10) for j in range(1,10) if i*j != x))\n"
TABLE_CHEAT = "x = int(input())\nprint({1: 2024, 11: 2025, 24: 1929}.get(x, 0))\n"   # passes the samples only
TABLE_WRONG = "print(0)\n"
TABLE_NAME_ERROR = "x = int(input())\nprint(y)\n"
LOOP = "while True:\n    pass\n"
ZIG_OK = ("class Solution:\n    def zigzagTraversal(self, grid: List[List[int]]) -> List[int]:\n"
          "        out = []; k = 0\n        for i, row in enumerate(grid):\n"
          "            for v in (row if i % 2 == 0 else row[::-1]):\n"
          "                if k % 2 == 0: out.append(v)\n                k += 1\n        return out\n\n"
          "print(Solution().zigzagTraversal([[1, 2], [3, 4]]))\n")   # example call must be removed
ZIG_WRONG = "class Solution:\n    def zigzagTraversal(self, grid: List[List[int]]) -> List[int]:\n        return []\n"


@unittest.skipUnless(os.path.exists(DATA_FILE), "data/LiveCodeBench/test6.jsonl not available")
class TestPyCapsuleLiveCodeBench(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dataset = LiveCodeBench("fake", output_dir="/tmp/lcb_pycapsule_test_results")
        cls.points = {}
        for i in range(len(dataset)):
            point = dataset.process(dataset.data.iloc[i])
            cls.points[point["task_id"]] = point

    def run_task(self, task_id, responses, trace=False, attempts=3):
        llm = FakeLLM(responses)
        capsule = PyCapsule_LiveCodeBench(LocalContainer("synk_lcb_test", timeout=300), llm,
                                          maximum_attempts=attempts, timeout=2, trace_feedback=trace)
        flag, fix_attempts, error_trace = capsule(self.points[task_id])
        return flag, fix_attempts, error_trace, capsule, llm

    def test_stdin_pass_first_try(self):
        flag, attempts, _, capsule, _ = self.run_task("abc387_b", [reply(TABLE_OK)])
        self.assertEqual((flag, attempts), (0, 0))
        self.assertEqual(capsule.last_task_details["public_cleared_attempt"], 0)
        self.assertEqual(capsule.last_task_details["private_cleared_attempt"], 0)

    def test_functional_pass_and_example_call_removed(self):
        flag, attempts, _, _, _ = self.run_task("3708", [reply(ZIG_OK)])
        self.assertEqual((flag, attempts), (0, 0))

    def test_public_failure_gets_detailed_feedback(self):
        flag, attempts, trace, _, llm = self.run_task("abc387_b", [reply(TABLE_WRONG), reply(TABLE_OK)])
        self.assertEqual((flag, attempts, trace), (0, 1, [["AssertionError"]]))
        self.assertIn("expected output: '2024'", llm.prompts[1])

    def test_private_failure_gets_generic_feedback_and_is_recorded(self):
        flag, attempts, trace, capsule, llm = self.run_task("abc387_b", [reply(TABLE_CHEAT), reply(TABLE_OK)])
        self.assertEqual((flag, attempts, trace), (0, 1, [["PrivateTestFailed"]]))
        self.assertIn("hidden test", llm.prompts[1])
        self.assertNotIn("2024", llm.prompts[1])
        details = capsule.last_task_details
        self.assertEqual((details["public_cleared_attempt"], details["private_cleared_attempt"]), (0, 1))
        self.assertEqual(details["private_failure_types"], ["wrong_answer"])

    def test_regression_after_public_cleared_gets_detailed_feedback(self):
        _, _, trace, _, llm = self.run_task("abc387_b", [reply(TABLE_CHEAT), reply(TABLE_NAME_ERROR), reply(TABLE_OK)])
        self.assertEqual(trace, [["PrivateTestFailed"], ["NameError"]])
        self.assertIn("name 'y' is not defined", llm.prompts[2])

    def test_public_never_cleared_is_a_fail(self):
        flag, attempts, _, capsule, _ = self.run_task("abc387_b", [reply(TABLE_WRONG)] * 4)
        self.assertNotEqual(flag, 0)
        self.assertEqual(attempts, 3)
        self.assertFalse(capsule.last_task_details["public_cleared"])

    def test_time_limit_has_its_own_feedback(self):
        flag, _, trace, _, llm = self.run_task("abc387_b", [reply(LOOP), reply(TABLE_OK)])
        self.assertEqual((flag, trace), (0, [["TimeLimitExceeded"]]))
        self.assertIn("time limit", llm.prompts[1])

    def test_repeated_code_fence_is_recovered(self):
        response = "### Code\n```\n```python\n" + TABLE_OK + "```"
        flag, attempts, _, _, _ = self.run_task("abc387_b", [response])
        self.assertEqual((flag, attempts), (0, 0))

    def test_no_code_gets_explicit_feedback(self):
        flag, _, trace, _, llm = self.run_task("abc387_b", ["I could not solve it.", reply(TABLE_OK)])
        self.assertEqual((flag, trace), (0, [["NoCodeFound"]]))
        self.assertIn("did not contain any code", llm.prompts[1])

    def test_trace_is_appended_to_public_failures_only(self):
        _, _, _, capsule, llm = self.run_task("3708", [reply(ZIG_WRONG), reply(ZIG_OK)], trace=True)
        self.assertIn("Execution trace of your code on public test case 1", llm.prompts[1])
        self.assertEqual(len(capsule.trace_log), 1)
        # private failure: no trace, it would reveal the hidden input
        _, _, _, capsule, llm = self.run_task("abc387_b", [reply(TABLE_CHEAT), reply(TABLE_OK)], trace=True)
        self.assertNotIn("Execution trace", llm.prompts[1])
        self.assertEqual(capsule.trace_log, [])


if __name__ == "__main__":
    unittest.main()
