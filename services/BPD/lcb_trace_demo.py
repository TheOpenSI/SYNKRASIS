# =============================================================================================
# Run BPD on a saved LiveCodeBench response and print what it produces. Everything runs in THIS
# process (no subprocess), so you can start it under a debugger and step through main().
#
#   python services/BPD/lcb_trace_demo.py                              # task 3763, attempt 0 of lcb_nano_30
#   python services/BPD/lcb_trace_demo.py --task arc194_c --attempt 2 --run-dir experiment_results/bpd_replay/trace/rep0
#   python services/BPD/lcb_trace_demo.py --task abc388_g --test 2     # trace public test number 2
#   python services/BPD/lcb_trace_demo.py --full                       # complete report (source listing, no shortening)
#   python services/BPD/lcb_trace_demo.py --via-subprocess             # the exact path PyCapsule uses
#
# What the pieces are (the production path is the same, only wrapped in a subprocess):
#   LCBHarness.extract_code            raw LLM response  -> code
#   LCBHarness.build_traceable_source  code              -> source BPD runs (typing import, example calls removed)
#   lcb_trace_worker.trace_request     source + test     -> BreakpointDebugger.run_expression -> report
#   LCBTracer.feedback_text            report            -> text appended to the fix query
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import argparse

from data.LiveCodeBench.LiveCodeBench import LiveCodeBench
from services.BPD.lcb_trace import LCBTracer
from services.BPD.lcb_trace_worker import trace_request
from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness

MAX_CHARS = 12000     # size budget of the concise report
MAX_STEPS = 300000    # executed lines before the trace is abandoned


def banner(title: str) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}")


def load_task(task_id: str) -> dict:
    """The processed data point (prompt, public/private tests, entry point, test type) of a task."""
    dataset = LiveCodeBench(model_name = "demo")
    for index in range(len(dataset.data)):
        data_point = dataset.process(dataset.data.iloc[index])
        if data_point["task_id"] == task_id:
            return data_point
    raise SystemExit(f"Task {task_id} not found in the dataset")


def load_response(run_dir: str, task_id: str, attempt: int) -> str:
    path = os.path.join(run_dir, "responses", f"task_{task_id}", f"attempt_{attempt}_response.txt")
    print(f"Reading {path}")
    with open(path, "r") as f:
        return f.read()


def make_request(source: str, data_point: dict, test: dict, full: bool) -> dict:
    return {"code": source, "mode": data_point["test_type"], "entry_point": data_point["entry_point"],
            "input": test["input"], "expected": test["output"],
            "max_chars": MAX_CHARS, "max_steps": MAX_STEPS, "full": full}


def pick_test(source: str, data_point: dict, test_number: int, full: bool) -> tuple[int, dict, dict]:
    """
    Trace the public tests in order and stop at the first one the code gets wrong (or crashes on).
    If every test passes, or test_number is given, that test is used. Returns (index, test, result).
    """
    tests = data_point["public_test"]
    candidates = [test_number - 1] if test_number else range(len(tests))
    result, index = None, 0
    for index in candidates:
        result = trace_request(make_request(source, data_point, tests[index], full))
        failed = result["error"] is not None or result["matches"] is False
        print(f"  public test {index + 1}: traced={result['ok']} matches={result['matches']} "
              f"error={result['error']} steps={result['steps']}")
        if failed or not result["ok"]:
            break
    return index, tests[index], result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default="experiment_results/lcb_nano_30")
    parser.add_argument("--task", default="3763")
    parser.add_argument("--attempt", type=int, default=0)
    parser.add_argument("--test", type=int, default=None, help="public test number (1-based), default: first failing")
    parser.add_argument("--full", action="store_true", help="full default report instead of the concise one")
    parser.add_argument("--via-subprocess", action="store_true", help="use LCBTracer, the path PyCapsule takes")
    args = parser.parse_args()

    harness = LCBHarness()

    # 1. the task and the LLM's saved response
    data_point = load_task(args.task)
    response = load_response(args.run_dir, args.task, args.attempt)

    # 2. response -> code -> the source BPD will run
    code = harness.extract_code(response)
    source = harness.build_traceable_source(data_point, code)
    banner(f"SOURCE BPD RUNS ({data_point['test_type']}, entry point {data_point['entry_point']})")
    for number, line in enumerate(source.split("\n"), start=1):
        print(f"{number:3} | {line}")

    # 3. trace (in this process), or through LCBTracer like PyCapsule does
    banner("TRACING THE PUBLIC TESTS")
    if args.via_subprocess:
        traced = LCBTracer(harness, MAX_CHARS).trace_first_failing_public_test(data_point, code)
        if traced is None:
            print("No failing public test could be traced (all pass, or the code cannot be traced).")
            return
        index, test, report = traced["test_index"], {"input": traced["input"], "output": traced["expected"]}, traced["report"]
    else:
        index, test, result = pick_test(source, data_point, args.test, args.full)
        if not result["ok"]:
            print(f"Could not trace: {result['error']}")
            return
        report = result["report"]
        print(f"\nProgram output / returned value: {result['output']!r}")

    # 4. what was traced and the report itself
    banner(f"PUBLIC TEST {index + 1}: input {test['input']!r}, expected {test['output']!r}")
    print(report)

    # 5. what PyCapsule appends to the fix query (public failures only)
    banner("TEXT APPENDED TO THE FIX QUERY")
    print(LCBTracer(harness, MAX_CHARS).feedback_text({"test_index": index, "report": report}))


if __name__ == "__main__":
    main()
