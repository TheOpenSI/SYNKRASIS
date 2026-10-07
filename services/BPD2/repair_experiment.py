"""
One-shot repair experiment: does a trace in the feedback help the model fix a known buggy program?

  python -u services/BPD2/repair_experiment.py [--problems experiment_results/bpd2_repair/problems.json]
                                               [--out experiment_results/bpd2_repair] [--limit N] [--fake]

Per problem and condition the buggy program is the model's "first answer" (replayed, no API call), it fails a public
test, the model gets ONE repair attempt with the feedback of that condition, then public and private tests decide:
  baseline  normal error message
  trace_v1  + old BPD concise trace (services/BPD)
  trace_v2  + BPD2 compact trace
Sequential, resumable. --fake: no API calls, the 'model' answers with the buggy code again (checks the plumbing).
"""
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import argparse
import json
import time
import types

for _name in ("scipy", "scipy.optimize"):
    try:
        __import__(_name)
    except ModuleNotFoundError:
        sys.modules[_name] = types.ModuleType(_name)
sys.modules["scipy.optimize"].curve_fit = getattr(sys.modules["scipy.optimize"], "curve_fit", None)

from data.LiveCodeBench.LiveCodeBench import LiveCodeBench
from services.BPD2.pycapsule_bpd2 import PyCapsule_LiveCodeBench_BPD2
from services.Container.LocalContainer import LocalContainer
from services.LLM.LLMBase import LLMBase
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench
from services.PyCapsule.livecodebench_harness.run_lcb_replay import ReplayFirstResponseLLM

CONDITIONS = ["baseline", "trace_v1", "trace_v2"]


def as_response(code: str) -> str:
    return f"### Step-by-step reasoning\nThe solution is below.\n\n### Requirements\nNone\n\n### Code\n```python\n{code}\n```"


class FakeLLM(ReplayFirstResponseLLM):
    """Replays the first answer, then answers with the same code again (no API)."""
    def __init__(self, first_response: str) -> None:
        LLMBase.__init__(self, "fake", enable_chat_history=True, max_history=1)
        self._first_response = first_response
        self.prompts = []

    def generate_response(self, user_prompt, context=None, suppress_conversation_history=True):
        self.prompts.append(user_prompt)
        if self._first_response is not None:
            return super().generate_response(user_prompt, context, suppress_conversation_history)
        return self.first_copy

    def cleanup(self):
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problems", default="experiment_results/bpd2_repair/problems.json")
    parser.add_argument("--out", default="experiment_results/bpd2_repair")
    parser.add_argument("--model", default="gpt-5-nano-2025-08-07")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fake", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    results_path = os.path.join(args.out, "results_fake.jsonl" if args.fake else "results.jsonl")
    with open(args.problems) as f:
        problems = json.load(f)[:args.limit]
    done = set()
    if os.path.exists(results_path):
        with open(results_path) as f:
            done = {(r["task_id"], r["condition"]) for r in map(json.loads, f)}

    dataset = LiveCodeBench("repair", output_dir=os.path.join(args.out, "_dataset"))
    points = {}
    for i in range(len(dataset.data)):
        point = dataset.process(dataset.data.iloc[i])
        points[point["task_id"]] = point

    container = LocalContainer(mount_dir_name="synk_bpd2_repair", timeout=1800)
    for problem in problems:
        for condition in CONDITIONS:
            if (problem["task_id"], condition) in done:
                continue
            first = as_response(problem["code"])
            if args.fake:
                llm = FakeLLM(first)
                llm.first_copy = first
            else:
                llm = ReplayFirstResponseLLM(first, model_name=args.model, enable_chat_history=True, max_history=1)
            kwargs = dict(pycapsule_container=container, llm=llm, maximum_attempts=1,
                          response_log_dir=os.path.join(args.out, "responses_fake" if args.fake else "responses", condition))
            capsule = (PyCapsule_LiveCodeBench_BPD2(**kwargs) if condition == "trace_v2" else
                       PyCapsule_LiveCodeBench(trace_feedback=(condition == "trace_v1"), **kwargs))
            print(f"\n===== {problem['task_id']} [{problem['kind']}] {condition}: {problem['description']}", flush=True)
            started = time.time()
            flag, attempts, error_trace = capsule(points[problem["task_id"]])
            details = capsule.last_task_details
            record = {"task_id": problem["task_id"], "kind": problem["kind"], "mutation": problem["description"],
                      "condition": condition, "first_error": error_trace[0][0] if error_trace else None,
                      "repaired_public": details["public_cleared"], "repaired_full": details["private_cleared"],
                      "seconds": round(time.time() - started),
                      "trace_chars": capsule.trace_log[0]["chars"] if capsule.trace_log else 0}
            with open(results_path, "a") as f:
                f.write(json.dumps(record) + "\n")
            print(f"===== RESULT {json.dumps(record)}", flush=True)
            if args.fake and condition != "baseline":
                print("----- fix query sent to the model:\n" + llm.prompts[1], flush=True)
            capsule.cleanup()
            llm.cleanup()


if __name__ == "__main__":
    main()
