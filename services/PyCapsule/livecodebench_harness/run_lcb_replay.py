# =============================================================================================
# Replay experiment: does a BPD execution trace in the public failure feedback help?
#
# For every task that did not clear the private tests at attempt 0 in a previous run, the saved
# attempt 0 response is replayed (so both arms start from the same code and chat history) and the
# fix loop runs with real LLM calls, once per arm:
#   baseline - normal feedback
#   trace    - normal feedback + concise BPD trace of the first failing public test
# Runs are sequential. Usage (repo root):
#   python -u services/PyCapsule/livecodebench_harness/run_lcb_replay.py --reps 1
# Output (--output-dir): results.jsonl (one line per run, resumable) and
#   <arm>/rep<r>/responses/task_<id>/attempt_<n>_{query,response}.txt
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import argparse
import json
import time
import types

try:
    import scipy.optimize  # noqa: F401
except ModuleNotFoundError:
    # scipy is only used by DDI (fresh_start experiments), not needed here.
    sys.modules["scipy"] = types.ModuleType("scipy")
    sys.modules["scipy.optimize"] = types.ModuleType("scipy.optimize")
    sys.modules["scipy.optimize"].curve_fit = None

from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from services.Container.LocalContainer import LocalContainer
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench
from data.LiveCodeBench.LiveCodeBench import LiveCodeBench

ARMS = {"baseline": False, "trace": True}


class ReplayFirstResponseLLM(OpenAI_GPT):
    """Returns a saved response for the first generation (attempt 0), real LLM calls after that."""

    def __init__(self, first_response: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._first_response = first_response

    def generate_response(self, user_prompt, context=None, suppress_conversation_history=True):
        if self._first_response is None:
            return super().generate_response(user_prompt, context, suppress_conversation_history)
        answer, self._first_response = self._first_response, None
        if self.enable_chat_history:  # same bookkeeping as OpenAI_GPT.generate_response
            if not self.chat_history:
                self.init_chat_history(user_prompt)
            self.chat_history.add_interaction(user_prompt, answer)
        return answer


def failed_at_attempt_0(source_dir: str, model: str) -> list[str]:
    with open(os.path.join(source_dir, f"{model}_LiveCodeBench_results.json")) as f:
        results = json.load(f)
    return [r["task_id"] for r in results if r["private_cleared_attempt"] != 0]


def already_done(results_path: str) -> set[tuple]:
    if not os.path.exists(results_path):
        return set()
    with open(results_path) as f:
        return {(r["arm"], r["rep"], r["task_id"]) for r in map(json.loads, f)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="experiment_results/lcb_nano_30")
    parser.add_argument("--output-dir", default="experiment_results/bpd_replay")
    parser.add_argument("--model", default="gpt-5-nano-2025-08-07")
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--tasks", default=None, help="comma separated task ids, default: all that failed attempt 0")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    results_path = os.path.join(args.output_dir, "results.jsonl")
    tasks = args.tasks.split(",") if args.tasks else failed_at_attempt_0(args.source_dir, args.model)
    print(f"Tasks ({len(tasks)}): {tasks}")

    dataset = LiveCodeBench(model_name = args.model, output_dir = os.path.join(args.output_dir, "_dataset"))
    points = {}
    for i in range(len(dataset.data)):
        point = dataset.process(dataset.data.iloc[i])
        points[point["task_id"]] = point

    done = already_done(results_path)
    container = LocalContainer(mount_dir_name = "synk_lcb_replay", timeout = 1800)

    for rep in range(args.reps):
        for task_id in tasks:
            for arm, use_trace in ARMS.items():
                if (arm, rep, task_id) in done:
                    continue
                with open(os.path.join(args.source_dir, "responses", f"task_{task_id}", "attempt_0_response.txt")) as f:
                    first_response = f.read()
                llm = ReplayFirstResponseLLM(first_response, model_name = args.model,
                                             enable_chat_history = True, max_history = 1)
                pycapsule = PyCapsule_LiveCodeBench(
                    pycapsule_container = container, llm = llm, maximum_attempts = args.max_attempts,
                    response_log_dir = os.path.join(args.output_dir, arm, f"rep{rep}", "responses"),
                    trace_feedback = use_trace)

                print(f"\n===== RUN arm={arm} rep={rep} task={task_id} =====", flush=True)
                started = time.time()
                flag, attempts, error_trace = pycapsule(points[task_id])
                record = {"arm": arm, "rep": rep, "task_id": task_id, "status": "pass" if flag == 0 else "fail",
                          "fix_attempts": attempts, "error_trace": error_trace,
                          "seconds": round(time.time() - started), "traces_attached": pycapsule.trace_log,
                          **pycapsule.last_task_details}
                with open(results_path, "a") as f:
                    f.write(json.dumps(record) + "\n")
                print(f"===== RESULT {json.dumps(record)}", flush=True)
                pycapsule.cleanup()
                llm.cleanup()


if __name__ == "__main__":
    main()
