# =============================================================================================
# Report of a LiveCodeBench experiment, built from the result files of its runs:
#   no_bpd          all problems, the fix queries have no execution trace.
#   bpd_1_trace     the problems no_bpd FAILED with a wrong answer (an AssertionError in the error trace),
#                   re-run with one execution trace in a fix query.
#   bpd_all_traces  the same problems, a trace for every wrong answer in a fix query.
# A trace is only given for a wrong answer, so those are the problems where the runs can differ.
#
# Usage:
#   python lcb_report.py <output_dir> <model_name>
# or from code: save_report(model_name, output_dir)
# =============================================================================================

import json
import os
import sys
from typing import Optional

BASELINE_RUN = "no_bpd"
BPD_RUNS = {"bpd_1_trace": "BPD, 1 trace",
            "bpd_all_traces": "BPD, all traces"}


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
    baseline = load_results(results_path(model_name, output_dir, BASELINE_RUN))
    if baseline is None:
        return f"No results of the run without BPD for {model_name} in {output_dir}."

    total = len(baseline)
    passed = [r for r in baseline if r["status"] == "pass"]
    with_assertion = [r for r in baseline if had_assertion(r)]
    bpd_set = [r for r in baseline if failed_with_assertion(r)]
    bpd_ids = {r["task_id"] for r in bpd_set}
    public_cleared = lambda results: sum(bool(r["public_cleared"]) for r in results)
    first_generation = lambda results: sum(r["fix_mode_attempt_count"] == 0 for r in results)

    def count(label: str, number: int, of: Optional[int] = None) -> str:
        text = f"  {label:<54}{number:>5}"
        return text + (f" / {of:<5}{100 * number / of if of else 0:6.1f}%" if of is not None else "")

    rows = [f"LiveCodeBench report: {model_name}", "=" * 78,
            f"WITHOUT BPD (all {total} problems)",
            count("passed (all public and hidden tests)", len(passed), total),
            count("    on the first generation", first_generation(passed)),
            count("    after fix attempts", len(passed) - first_generation(passed)),
            count("cleared the public tests", public_cleared(baseline), total),
            count("had a wrong answer (AssertionError) at some attempt", len(with_assertion)),
            count("    recovered and passed", sum(r["status"] == "pass" for r in with_assertion)),
            count("    still failed  (these are re-run with BPD)", len(bpd_set)),
            "", f"WITH BPD (re-run on the {len(bpd_set)} problems that still failed with a wrong answer)"]

    runs = {}       # run name -> results, None if the run did not start
    for name in BPD_RUNS:
        runs[name] = load_results(results_path(model_name, output_dir, name))

    def cell(run_name: str, value) -> str:
        results = runs[run_name]
        if results is None:
            return "not run".rjust(18)
        return str(value(results)).rjust(18)

    def partial(run_name: str) -> str:
        results = runs[run_name]
        return "" if results is None or len(results) >= len(bpd_set) else f"{run_name}: {len(results)} of {len(bpd_set)} problems done (partial)"

    n = len(bpd_set)
    header = f"  {'':<54}" + "".join(BPD_RUNS[name].rjust(18) for name in BPD_RUNS)
    rows += [header]
    pct = lambda number: f"{number} ({100 * number / n:.1f}%)" if n else f"{number}"
    rows += [f"  {'passed':<54}" + "".join(cell(name, lambda r: pct(sum(x['status'] == 'pass' for x in r))) for name in BPD_RUNS),
             f"  {'    on the first generation (before any trace)':<54}" + "".join(cell(name, lambda r: first_generation([x for x in r if x['status'] == 'pass'])) for name in BPD_RUNS),
             f"  {'    after fix attempts':<54}" + "".join(cell(name, lambda r: sum(x['status'] == 'pass' and x['fix_mode_attempt_count'] > 0 for x in r)) for name in BPD_RUNS),
             f"  {'cleared the public tests':<54}" + "".join(cell(name, lambda r: pct(public_cleared(r))) for name in BPD_RUNS),
             f"  {'  (without BPD, the same problems: public cleared)':<54}{pct(public_cleared([r for r in baseline if r['task_id'] in bpd_ids])):>18}"]

    rows += ["", f"ALL {total} PROBLEMS, a BPD result replaces the first one on those {n} problems",
             f"  {'without BPD':<54}{len(passed):>5} / {total:<5}{100 * len(passed) / total:6.1f}%"]
    for name, label in BPD_RUNS.items():
        results = runs[name]
        if results is None:
            rows.append(f"  {label:<54}{'not run':>5}")
        else:
            total_passed = len(passed) + sum(r["status"] == "pass" for r in results)
            rows.append(f"  {label:<54}{total_passed:>5} / {total:<5}{100 * total_passed / total:6.1f}%")

    notes = [partial(name) for name in BPD_RUNS if partial(name)]
    rows += [""] + notes + ["Note: a BPD run asks the model again, a new sample at temperature > 0. A pass on the first generation",
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
