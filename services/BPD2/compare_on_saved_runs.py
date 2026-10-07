# Compact vs old concise trace on the saved first attempts of a run (no API calls).
#   python services/BPD2/compare_on_saved_runs.py [--run-dir experiment_results/lcb_nano_30] [--out experiment_results/bpd2/traces]
# For every task: the first public test the code gets wrong, else the first public test.
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import argparse
import json
import re
import types

for _name in ("scipy", "scipy.optimize"):          # DDI needs scipy, not used here
    if _name not in sys.modules:
        try:
            __import__(_name)
        except ModuleNotFoundError:
            sys.modules[_name] = types.ModuleType(_name)
sys.modules["scipy.optimize"].curve_fit = getattr(sys.modules["scipy.optimize"], "curve_fit", None)

from data.LiveCodeBench.LiveCodeBench import LiveCodeBench
from services.BPD import tracer as old_tracer
from services.BPD.lcb_trace_worker import trace_request as trace_old
from services.BPD2.lcb_trace2 import trace_request as trace_new
from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness


ORIGINAL_ON_LINE = old_tracer.TraceCollector._on_line   # the old worker patches it for its step limit and never restores it


def approx_tokens(text: str) -> int:
    return len(re.findall(r"\w+|[^\w\s]", text))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default="experiment_results/lcb_nano_30")
    parser.add_argument("--out", default="experiment_results/bpd2/traces")
    parser.add_argument("--attempt", type=int, default=0)
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    harness = LCBHarness()
    dataset = LiveCodeBench("cmp", output_dir="/tmp/bpd2_cmp_dataset")
    points = {}
    for i in range(len(dataset.data)):
        point = dataset.process(dataset.data.iloc[i])
        points[point["task_id"]] = point
    with open(os.path.join(args.run_dir, "gpt-5-nano-2025-08-07_LiveCodeBench_results.json")) as f:
        tasks = [r["task_id"] for r in json.load(f)]

    rows = []
    for task in tasks:
        point = points[task]
        with open(os.path.join(args.run_dir, "responses", f"task_{task}", f"attempt_{args.attempt}_response.txt")) as f:
            source = harness.build_traceable_source(point, harness.extract_code(f.read()))
        chosen = None
        for test in point["public_test"]:
            request = {"code": source, "mode": point["test_type"], "entry_point": point["entry_point"],
                       "input": test["input"], "expected": test["output"], "max_chars": 12000, "max_steps": 20000}
            new = trace_new(request)
            if not new["ok"] or new["matches"] is not True:
                chosen = (request, new); break
            chosen = chosen or (request, new)
        request, new = chosen
        # the old tracer has no time limit, do not run it where the new one gave up
        old = trace_old(request) if new["ok"] else {"report": ""}
        old_tracer.TraceCollector._on_line = ORIGINAL_ON_LINE
        rows.append((task, point["test_type"], approx_tokens(old["report"]), approx_tokens(new["report"]), new["ok"], new["error"]))
        with open(os.path.join(args.out, f"{task}.txt"), "w") as f:
            f.write(new["report"] if new["ok"] else f"NOT TRACED: {new['error']}")
        print(f"{task:9} {point['test_type']:10} old {rows[-1][2]:5}  compact {rows[-1][3]:5}  ok={new['ok']} err={new['error']}", flush=True)

    print(f"\ntotal approx tokens: old concise {sum(r[2] for r in rows)} -> compact {sum(r[3] for r in rows)}; "
          f"max old {max(r[2] for r in rows)} -> compact {max(r[3] for r in rows)}")


if __name__ == "__main__":
    main()
