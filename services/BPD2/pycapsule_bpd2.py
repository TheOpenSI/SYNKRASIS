"""
PyCapsule_LiveCodeBench whose public-failure feedback carries the BPD2 compact trace.
(The production class, with trace_feedback=True, carries the old BPD trace.)
"""
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from typing import Optional

from services.BPD2.lcb_trace2 import trace_request
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench

LEGEND = ("How to read it: only the lines that ran are listed, with the values after `#`. `x=1,2,3` are the values "
          "of x on successive executions of that line, `a..b` a run of consecutive numbers, `T/F` the outcome of a "
          "condition on each execution, `F×3` three equal values, `(iters 2,4)` the loop iterations the line ran in, "
          "`...` omitted middle values. Nested lines belong to the line above.")


class PyCapsule_LiveCodeBench_BPD2(PyCapsule_LiveCodeBench):

    def __init__(self, *args, max_steps: int = 20000, **kwargs) -> None:
        kwargs["trace_feedback"] = False          # the old trace is not used here
        super().__init__(*args, **kwargs)
        self.max_steps = max_steps

    def _trace_section(self, user_query: dict) -> str:
        found = self._first_failing_public_test(user_query)
        if found is None:
            return ""
        index, report = found
        self.trace_log.append({"task_id": user_query["task_id"], "test_index": index, "chars": len(report)})
        return (f"\n\nExecution trace of your code on public test case {index + 1}. {LEGEND}\n{report}\n"
                "Find the first point where the behaviour differs from what the problem requires and fix that logic.")

    def _first_failing_public_test(self, user_query: dict) -> Optional[tuple[int, str]]:
        source = self.harness.build_traceable_source(user_query, self._last_code)
        for index, test in enumerate(user_query["public_test"]):
            result = trace_request({"code": source, "mode": user_query["test_type"],
                                    "entry_point": user_query["entry_point"], "input": test["input"],
                                    "expected": test["output"], "max_steps": self.max_steps})
            if not result["ok"]:
                return None
            if result["error"] is not None or result["matches"] is False:
                return index, result["report"]
        return None
