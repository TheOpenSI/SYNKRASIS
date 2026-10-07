"""
100 LiveCodeBench problems: existing error handling (baseline) vs existing error handling + BPD2 trace (trace).

  python -u services/BPD2/compare100.py                 # runs everything that is missing, resumable
  python -u services/BPD2/compare100.py --summary       # only print the summary of what exists
  python -u services/BPD2/compare100.py --fake --out /tmp/x --limit 4    # no API, checks the plumbing

Stage 1: the first attempt of each problem is generated ONCE (the 30 problems of experiment_results/lcb_nano_30 reuse their
         saved first attempt and are only re-evaluated, no API call). Both arms start from this same answer.
Stage 2: every problem whose first attempt did not pass public AND private tests goes through the fix loop (5 attempts),
         once per arm. Public failures get the detailed error message (both arms) and the BPD2 trace (trace arm only).
Everything is sequential. Output (--out):  attempt0.jsonl, arms.jsonl, attempt0_responses/, arms/<arm>/responses/
"""
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import argparse
import json
import math
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
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench
from services.PyCapsule.livecodebench_harness.run_lcb_replay import ReplayFirstResponseLLM

ARMS = ["baseline", "trace"]
EXISTING_RUN = "experiment_results/lcb_nano_30"
MODEL = "gpt-5-nano-2025-08-07"


# -- selection ---------------------------------------------------------------------------------

def evenly(pool: list, count: int) -> list:
    return [pool[int(i * len(pool) / count)] for i in range(count)] if count > 0 else []


def select_problems(all_ids: list[str], total: int = 100) -> list[str]:
    """The problems of the existing run, plus others so that the leetcode share matches the dataset."""
    with open(os.path.join(EXISTING_RUN, f"{MODEL}_LiveCodeBench_results.json")) as f:
        existing = [r["task_id"] for r in json.load(f)]
    is_leetcode = lambda task_id: task_id.isdigit()
    want_leetcode = round(total * sum(map(is_leetcode, all_ids)) / len(all_ids))
    rest = [t for t in all_ids if t not in existing]
    more_leetcode = max(0, want_leetcode - sum(map(is_leetcode, existing)))
    chosen = evenly([t for t in rest if is_leetcode(t)], more_leetcode)
    chosen += evenly([t for t in rest if not is_leetcode(t)], total - len(existing) - len(chosen))
    return existing + chosen


# -- fake LLM (plumbing check) -----------------------------------------------------------------

class FakeGenerator(LLMBase):
    """No API: a stub solution for every question, the same stub again for every fix."""
    def __init__(self, point: dict) -> None:
        super().__init__("fake", enable_chat_history=True, max_history=1)
        code = ("class Solution:\n    def %s(self, *args):\n        return None\n" % point["entry_point"]
                if point["test_type"] == "functional" else "print(0)\n")
        self.answer = f"### Step-by-step reasoning\nstub\n\n### Requirements\nNone\n\n### Code\n```python\n{code}```"

    def generate_response(self, user_prompt, context=None, suppress_conversation_history=True):
        return self.answer

    def cleanup(self):
        pass


# -- helpers -----------------------------------------------------------------------------------

def read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path: str, record: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def saved_first_response(task_id: str, out: str) -> str:
    for directory in (os.path.join(out, "attempt0_responses"), os.path.join(EXISTING_RUN, "responses")):
        path = os.path.join(directory, f"task_{task_id}", "attempt_0_response.txt")
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
    raise FileNotFoundError(task_id)


# -- stages ------------------------------------------------------------------------------------

def stage1(args, points: dict, ids: list[str], container) -> None:
    path = os.path.join(args.out, "attempt0.jsonl")
    done = {r["task_id"] for r in read_jsonl(path)}
    for task_id in ids:
        if task_id in done:
            continue
        point = points[task_id]
        reusable = os.path.exists(os.path.join(EXISTING_RUN, "responses", f"task_{task_id}", "attempt_0_response.txt"))
        if reusable and not args.fake:
            llm = ReplayFirstResponseLLM(saved_first_response(task_id, args.out), model_name=MODEL,
                                         enable_chat_history=True, max_history=1)
        elif args.fake:
            llm = FakeGenerator(point)
        else:
            llm = OpenAI_GPT(model_name=MODEL, enable_chat_history=True, max_history=1)
        capsule = PyCapsule_LiveCodeBench(container, llm, maximum_attempts=0,
                                          response_log_dir=os.path.join(args.out, "attempt0_responses"))
        print(f"\n===== STAGE 1 {task_id} ({point['test_type']}) {'replay' if reusable and not args.fake else 'generate'}", flush=True)
        started = time.time()
        capsule(point)
        details = capsule.last_task_details
        record = {"task_id": task_id, "type": point["test_type"], "reused": reusable,
                  "public_pass0": details["public_cleared"], "full_pass0": details["private_cleared"],
                  "seconds": round(time.time() - started)}
        append_jsonl(path, record)
        print(f"===== RESULT {json.dumps(record)}", flush=True)
        capsule.cleanup(); llm.cleanup()


def stage2(args, points: dict, container) -> None:
    attempt0 = read_jsonl(os.path.join(args.out, "attempt0.jsonl"))
    failing = [r["task_id"] for r in attempt0 if not r["full_pass0"]]
    path = os.path.join(args.out, "arms.jsonl")
    done = {(r["task_id"], r["arm"]) for r in read_jsonl(path)}
    print(f"\nStage 2: {len(failing)} problems did not fully pass their first attempt", flush=True)
    for task_id in failing:
        for arm in ARMS:
            if (task_id, arm) in done:
                continue
            point = points[task_id]
            first = saved_first_response(task_id, args.out)
            if args.fake:
                llm = FakeGenerator(point)
                llm.answer = first
            else:
                llm = ReplayFirstResponseLLM(first, model_name=MODEL, enable_chat_history=True, max_history=1)
            kwargs = dict(pycapsule_container=container, llm=llm, maximum_attempts=5,
                          response_log_dir=os.path.join(args.out, "arms", arm, "responses"))
            capsule = PyCapsule_LiveCodeBench_BPD2(**kwargs) if arm == "trace" else PyCapsule_LiveCodeBench(**kwargs)
            print(f"\n===== STAGE 2 {task_id} ({point['test_type']}) arm={arm}", flush=True)
            started = time.time()
            flag, attempts, error_trace = capsule(point)
            record = {"task_id": task_id, "arm": arm, "type": point["test_type"], "status": "pass" if flag == 0 else "fail",
                      "fix_attempts": attempts, "error_trace": error_trace, "seconds": round(time.time() - started),
                      "traces_attached": len(capsule.trace_log), "trace_chars": [t["chars"] for t in capsule.trace_log],
                      **capsule.last_task_details}
            append_jsonl(path, record)
            print(f"===== RESULT {json.dumps(record)}", flush=True)
            capsule.cleanup(); llm.cleanup()


# -- summary -----------------------------------------------------------------------------------

def sign_test_p(only_a: int, only_b: int) -> float:
    """Two sided exact sign test on the discordant pairs."""
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def summary(out: str) -> None:
    attempt0 = read_jsonl(os.path.join(out, "attempt0.jsonl"))
    arms = read_jsonl(os.path.join(out, "arms.jsonl"))
    if not attempt0:
        print("nothing yet"); return
    n = len(attempt0)
    pass0 = sum(r["full_pass0"] for r in attempt0)
    print(f"Problems: {n} | first attempt passes public+private: {pass0} ({100 * pass0 / n:.0f}%) | "
          f"passes public only: {sum(r['public_pass0'] and not r['full_pass0'] for r in attempt0)} | "
          f"fails public: {sum(not r['public_pass0'] for r in attempt0)}")
    by = {(r["task_id"], r["arm"]): r for r in arms}
    failing = [r["task_id"] for r in attempt0 if not r["full_pass0"]]
    paired = [t for t in failing if (t, "baseline") in by and (t, "trace") in by]
    print(f"\nFix loop (5 attempts) on {len(failing)} failing problems, {len(paired)} finished in both arms:")
    for arm in ARMS:
        runs = [by[(t, arm)] for t in paired]
        if not runs:
            continue
        solved = [r for r in runs if r["status"] == "pass"]
        print(f"  {arm:9} solved {len(solved):2}/{len(runs)}   public cleared {sum(r['public_cleared'] for r in runs):2}   "
              f"mean fix attempts (solved) {sum(r['fix_attempts'] for r in solved) / max(1, len(solved)):.1f}   "
              f"mean seconds {sum(r['seconds'] for r in runs) / len(runs):.0f}")
    only_base = [t for t in paired if by[(t, "baseline")]["status"] == "pass" and by[(t, "trace")]["status"] != "pass"]
    only_trace = [t for t in paired if by[(t, "trace")]["status"] == "pass" and by[(t, "baseline")]["status"] != "pass"]
    print(f"  baseline only solved: {only_base}\n  trace only solved:    {only_trace}   (sign test p = {sign_test_p(len(only_base), len(only_trace)):.2f})")
    for label, group in (("public failure at attempt 0", [t for t in paired if not next(r for r in attempt0 if r['task_id'] == t)["public_pass0"]]),
                         ("private failure at attempt 0", [t for t in paired if next(r for r in attempt0 if r['task_id'] == t)["public_pass0"]])):
        if group:
            print(f"  {label}: {len(group)} problems, solved baseline {sum(by[(t, 'baseline')]['status'] == 'pass' for t in group)}"
                  f" / trace {sum(by[(t, 'trace')]['status'] == 'pass' for t in group)}")
    total_pass = {arm: pass0 + sum(by[(t, arm)]["status"] == "pass" for t in failing if (t, arm) in by) for arm in ARMS}
    if len(paired) == len(failing):
        print(f"\nOverall pass rate after the fix loop: baseline {total_pass['baseline']}/{n}, trace {total_pass['trace']}/{n}")
    chars = [c for r in arms if r["arm"] == "trace" for c in r["trace_chars"]]
    if chars:
        print(f"Traces attached: {len(chars)}, median {sorted(chars)[len(chars) // 2]} chars, max {max(chars)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="experiment_results/compare100")
    parser.add_argument("--total", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None, help="only the first N selected problems")
    parser.add_argument("--ids", default=None, help="comma separated task ids instead of the selection (plumbing checks)")
    parser.add_argument("--fake", action="store_true", help="no API calls, stub answers (plumbing check)")
    parser.add_argument("--stage1-only", action="store_true", help="only the first attempts, skip the fix loop")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.summary:
        summary(args.out); return

    dataset = LiveCodeBench("compare100", output_dir=os.path.join(args.out, "_dataset"))
    points = {}
    for i in range(len(dataset.data)):
        point = dataset.process(dataset.data.iloc[i])
        points[point["task_id"]] = point
    ids = args.ids.split(",") if args.ids else select_problems(list(points), args.total)[:args.limit]
    leetcode = sum(t.isdigit() for t in ids)
    print(f"Selected {len(ids)} problems ({leetcode} functional, {len(ids) - leetcode} stdin); "
          f"{sum(os.path.exists(os.path.join(EXISTING_RUN, 'responses', f'task_{t}')) for t in ids)} reuse a saved first attempt")
    json.dump(ids, open(os.path.join(args.out, "selected.json"), "w"))

    container = LocalContainer(mount_dir_name="synk_compare100", timeout=1800)
    stage1(args, points, ids, container)
    if args.stage1_only:
        return
    stage2(args, points, container)
    print("\n" + "=" * 70)
    summary(args.out)


if __name__ == "__main__":
    main()
