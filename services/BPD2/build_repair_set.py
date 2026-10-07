"""
Build the set of buggy programs for the repair experiment (no API calls).

  python services/BPD2/build_repair_set.py [--run-dir experiment_results/lcb_nano_30] [--out experiment_results/bpd2_repair/problems.json]

- mutants: the first attempt of every task that passed everything, with ONE injected bug that makes a public test fail
  (checked with the real test driver) and that BPD2 can trace.
- natural: the real first attempts that failed a public test.
"""
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import argparse
import json
import subprocess
import tempfile
import types

for _name in ("scipy", "scipy.optimize"):
    try:
        __import__(_name)
    except ModuleNotFoundError:
        sys.modules[_name] = types.ModuleType(_name)
sys.modules["scipy.optimize"].curve_fit = getattr(sys.modules["scipy.optimize"], "curve_fit", None)

from data.LiveCodeBench.LiveCodeBench import LiveCodeBench
from services.BPD2.lcb_trace2 import trace_request
from services.BPD2.mutate import list_mutants
from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness

harness = LCBHarness()


def run_public(code: str, point: dict, timeout: int = 10):
    """Runs the public tests with the production test driver. Returns (returncode, stderr)."""
    with tempfile.TemporaryDirectory() as directory:
        with open(os.path.join(directory, "solution.py"), "w") as f:
            f.write(harness.build_solution_content(point, code))
        with open(os.path.join(directory, "main.py"), "w") as f:
            f.write(harness.build_driver_content(point["public_test"], timeout))
        try:
            process = subprocess.run([sys.executable, os.path.join(directory, "main.py")], capture_output=True,
                                     text=True, timeout=timeout * len(point["public_test"]) + 10)
        except subprocess.TimeoutExpired:
            return -1, "timeout"
        return process.returncode, process.stderr


def traceable(code: str, point: dict) -> bool:
    """BPD2 can trace the first public test the code fails."""
    source = harness.build_traceable_source(point, code)
    for test in point["public_test"]:
        result = trace_request({"code": source, "mode": point["test_type"], "entry_point": point["entry_point"],
                                "input": test["input"], "expected": test["output"], "max_steps": 20000})
        if not result["ok"]:
            return False
        if result["matches"] is not True:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default="experiment_results/lcb_nano_30")
    parser.add_argument("--out", default="experiment_results/bpd2_repair/problems.json")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    dataset = LiveCodeBench("repair", output_dir="/tmp/bpd2_repair_dataset")
    points = {}
    for i in range(len(dataset.data)):
        point = dataset.process(dataset.data.iloc[i])
        points[point["task_id"]] = point
    with open(os.path.join(args.run_dir, "gpt-5-nano-2025-08-07_LiveCodeBench_results.json")) as f:
        results = json.load(f)

    def first_attempt_code(task: str) -> str:
        with open(os.path.join(args.run_dir, "responses", f"task_{task}", "attempt_0_response.txt")) as f:
            return harness.extract_code(f.read())

    problems = []
    for result in results:
        task, point = result["task_id"], points[result["task_id"]]
        if result["public_cleared_attempt"] != 0:
            problems.append({"task_id": task, "kind": "natural", "description": "real first attempt, failed a public test",
                             "line": None, "code": first_attempt_code(task)})
            print(f"{task:9} natural", flush=True)
            continue
        if result["private_cleared_attempt"] != 0:
            continue                                             # passes public but not private: no public failure to show
        base = harness.build_traceable_source(point, first_attempt_code(task))
        found = None
        for mutant in list_mutants(base, seed=args.seed)[:60]:
            code, _ = mutant.source, None
            returncode, stderr = run_public(code, point)
            if returncode != 1 or "infinite loop" in stderr or "SyntaxError" in stderr:
                continue
            if traceable(code, point):
                found = mutant
                break
        if found is None:
            print(f"{task:9} no usable mutant", flush=True)
            continue
        problems.append({"task_id": task, "kind": "mutant", "description": found.description,
                         "line": found.line, "code": found.source})
        print(f"{task:9} mutant: {found.description} (line {found.line})", flush=True)

    with open(args.out, "w") as f:
        json.dump(problems, f, indent=1)
    print(f"\n{len(problems)} problems ({sum(p['kind'] == 'mutant' for p in problems)} mutants, "
          f"{sum(p['kind'] == 'natural' for p in problems)} natural) -> {args.out}")


if __name__ == "__main__":
    main()
