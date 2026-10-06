# =============================================================================================
# Execution trace of an LLM solution on a LiveCodeBench public test, for the PyCapsule feedback.
#
# Usage:
# - LCBTracer(harness: LCBHarness, max_chars: int = 12000, timeout: int = 60)
# - trace_first_failing_public_test(user_query: dict, code: str) -> Optional[dict]
#       Runs the public tests in order under BPD (in a subprocess, lcb_trace_worker.py) and returns
#       {"test_index", "input", "expected", "report"} for the first one the code gets wrong or crashes
#       on. None when every public test passes or the code cannot be traced (syntax error, too many
#       steps, timeout), the normal error feedback is enough then.
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
import subprocess
from typing import Optional

from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness


class LCBTracer():
    WORKER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lcb_trace_worker.py")

    def __init__(self, harness: LCBHarness, max_chars: int = 12000, timeout: int = 60, max_steps: int = 300000) -> None:
        self.harness = harness
        self.max_chars = max_chars
        self.timeout = timeout
        self.max_steps = max_steps


    def trace_first_failing_public_test(self, user_query: dict, code: str) -> Optional[dict]:
        source = self.harness.build_traceable_source(user_query, code)
        for index, test in enumerate(user_query["public_test"]):
            result = self._run_worker(source, user_query, test)
            if result is None or not result["ok"]:
                return None
            if result["error"] is not None or result["matches"] is False:
                return {"test_index": index, "input": test["input"], "expected": test["output"],
                        "report": result["report"]}
        return None


    def _run_worker(self, source: str, user_query: dict, test: dict) -> Optional[dict]:
        request = {"code": source, "mode": user_query["test_type"], "entry_point": user_query["entry_point"],
                   "input": test["input"], "expected": test["output"],
                   "max_chars": self.max_chars, "max_steps": self.max_steps}
        try:
            process = subprocess.run([sys.executable, self.WORKER_PATH], input=json.dumps(request),
                                     capture_output=True, text=True, timeout=self.timeout)
            return json.loads(process.stdout.strip().splitlines()[-1])
        except (subprocess.TimeoutExpired, IndexError, json.JSONDecodeError):
            return None
