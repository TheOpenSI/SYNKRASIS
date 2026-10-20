# =============================================================================================
# Report of a LiveCodeBench experiment, built from the result files of its two runs:
#   1. "no_bpd": all problems, the fix queries have no execution trace.
#   2. "bpd": only the problems the first run FAILED with a wrong answer (an AssertionError in the
#      error trace), re-run with execution traces. A trace is only given for a wrong answer, so these
#      are the only problems where the two runs can differ.
#
# The report says, in this order:
#   - the accuracy without BPD (and how many problems had a wrong answer, how many of them recovered)
#   - what BPD did on the problems that still failed with a wrong answer
#   - how many problems cleared the public tests without and with BPD
#   - the accuracy over all problems if the BPD result replaces the first one on those problems
#
# Usage:
#   python lcb_report.py <output_dir> <model_name>
# or from code: build_report(model_name, output_dir)
# =============================================================================================

import json
import os
import sys
from typing import Optional

BASELINE_RUN = "no_bpd"
BPD_RUN = "bpd"


def had_assertion(result: dict) -> bool:
    """A wrong answer in some attempt: an AssertionError in the error trace (one list of error types per attempt)."""
    return any("AssertionError" in attempt for attempt in result["error_trace"])


def failed_with_assertion(result: dict) -> bool:
    """Still failed after all attempts, and had a wrong answer: the problems that are re-run with BPD."""
    return result["status"] == "fail" and had_assertion(result)


def results_path(model_name: str, output_dir: str, run_name: str) -> str:
    return os.path.join(output_dir, f"{model_name}_LiveCodeBench_results_{run_name}.json")


def load_results(path: str) -> Optional[list[dict]]:
    if not os.path.exists(path):
        return None
    with open(path, "r") as results_file:
        return json.load(results_file)


def build_report(model_name: str, output_dir: str) -> str:
    """
    Args:
        model_name (str): Model of the experiment (part of the name of the result files).
        output_dir (str): Directory with the result files (json).

    Returns:
        str: The report as text.
    """
    baseline = load_results(results_path(model_name, output_dir, BASELINE_RUN))
    if baseline is None:
        return f"No results of the run without BPD for {model_name} in {output_dir}."

    def line(label: str, count: int, total: Optional[int] = None) -> str:
        text = f"  {label:<52}{count:>5}"
        if total is not None:
            text += f" / {total:<5}{100 * count / total if total else 0:6.1f}%"
        return text

    total = len(baseline)
    passed = [r for r in baseline if r["status"] == "pass"]
    with_assertion = [r for r in baseline if had_assertion(r)]
    bpd_set = [r for r in baseline if failed_with_assertion(r)]
    bpd_ids = {r["task_id"] for r in bpd_set}

    rows = [f"LiveCodeBench report: {model_name}", "=" * 72,
            f"WITHOUT BPD (all {total} problems)",
            line("passed (all public and hidden tests)", len(passed), total),
            line("    on the first generation", sum(r["fix_mode_attempt_count"] == 0 for r in passed)),
            line("    after fix attempts", sum(r["fix_mode_attempt_count"] > 0 for r in passed)),
            line("cleared the public tests", sum(bool(r["public_cleared"]) for r in baseline), total),
            line("had a wrong answer (AssertionError) at some attempt", len(with_assertion)),
            line("    recovered and passed", sum(r["status"] == "pass" for r in with_assertion)),
            line("    still failed  (these are re-run with BPD)", len(bpd_set))]

    bpd = load_results(results_path(model_name, output_dir, BPD_RUN))
    rows += ["", f"WITH BPD (the {len(bpd_set)} problems that still failed with a wrong answer)"]
    if bpd is None:
        rows.append("  nothing to run, no problem failed with a wrong answer" if not bpd_set else "  not run yet")
        return "\n".join(rows)
    if len(bpd) < len(bpd_set):
        rows.append(f"  NOT FINISHED: {len(bpd)} of {len(bpd_set)} problems done, the numbers below are partial")

    bpd_passed = [r for r in bpd if r["status"] == "pass"]
    baseline_on_set = [r for r in baseline if r["task_id"] in bpd_ids]
    rows += [line("passed", len(bpd_passed), len(bpd_set)),
             line("    on the first generation (before any trace)", sum(r["fix_mode_attempt_count"] == 0 for r in bpd_passed)),
             line("    after fix attempts", sum(r["fix_mode_attempt_count"] > 0 for r in bpd_passed)),
             "",
             f"PUBLIC TESTS CLEARED ON THOSE {len(bpd_set)} PROBLEMS",
             line("without BPD", sum(bool(r["public_cleared"]) for r in baseline_on_set), len(bpd_set)),
             line("with BPD", sum(bool(r["public_cleared"]) for r in bpd), len(bpd_set)),
             "",
             f"ALL {total} PROBLEMS, the BPD result replaces the first one on those {len(bpd_set)}",
             line("passed", len(passed) + len(bpd_passed), total)]
    if bpd is not None and len(bpd) < len(bpd_set):
        rows.append("  (partial: the BPD run is not finished)")
    rows += ["", "Note: the BPD run asks the model again, a new sample at temperature > 0. A pass on the first generation",
             "happens before any trace is used, it shows how much the result moves by sampling alone."]
    return "\n".join(rows)


def save_report(model_name: str, output_dir: str) -> str:
    """Build the report, save it in output_dir and return it."""
    report = build_report(model_name, output_dir)
    file_name = f"{model_name.replace('/', '_')}_report.txt"
    with open(os.path.join(output_dir, file_name), "w") as report_file:
        report_file.write(report + "\n")
    return report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    print(save_report(model_name = sys.argv[2], output_dir = sys.argv[1]))
