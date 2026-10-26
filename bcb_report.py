# =============================================================================================
# Report of a BigCodeBench experiment, built from the result files of its runs:
#   no_bpd          all tasks, the fix queries have no execution trace.
#   bpd_1_trace     the tasks no_bpd FAILED with a wrong answer (a failed assertion, "AssertionError" in the error
#                   trace), re-run with one execution trace in a fix query.
#   bpd_all_traces  the same tasks, a trace for every failed assertion in a fix query.
# A trace is only given for a failed assertion, so those are the tasks where the runs can differ.
# A task passes when all its unit tests pass.
#
# Usage:
#   python bcb_report.py <output_dir> <model_name>
# or from code: save_report(model_name, output_dir)
# =============================================================================================

import os
import sys
from typing import Optional

from lcb_report import BASELINE_RUN, BPD_RUNS, failed_with_assertion, had_assertion, load_results
from lcb_report import results_path as _results_path

DATASET = "BigCodeBench"


def results_path(model_name: str, output_dir: str, run_name: str) -> str:
    return _results_path(model_name, output_dir, run_name, DATASET)


def build_report(model_name: str, output_dir: str) -> str:
    baseline = load_results(results_path(model_name, output_dir, BASELINE_RUN))
    if baseline is None:
        return f"No results of the run without BPD for {model_name} in {output_dir}."

    total = len(baseline)
    passed = [r for r in baseline if r["status"] == "pass"]
    with_assertion = [r for r in baseline if had_assertion(r)]
    bpd_set = [r for r in baseline if failed_with_assertion(r)]
    first_generation = lambda results: sum(r["fix_mode_attempt_count"] == 0 for r in results)

    def count(label: str, number: int, of: Optional[int] = None) -> str:
        text = f"  {label:<54}{number:>5}"
        return text + (f" / {of:<5}{100 * number / of if of else 0:6.1f}%" if of is not None else "")

    rows = [f"BigCodeBench report: {model_name}", "=" * 78,
            f"WITHOUT BPD (all {total} tasks)",
            count("passed (all unit tests)", len(passed), total),
            count("    on the first generation", first_generation(passed)),
            count("    after fix attempts", len(passed) - first_generation(passed)),
            count("had a failed assertion at some attempt", len(with_assertion)),
            count("    recovered and passed", sum(r["status"] == "pass" for r in with_assertion)),
            count("    still failed  (these are re-run with BPD)", len(bpd_set)),
            "", f"WITH BPD (re-run on the {len(bpd_set)} tasks that still failed with a failed assertion)"]

    runs = {name: load_results(results_path(model_name, output_dir, name)) for name in BPD_RUNS}
    n = len(bpd_set)
    pct = lambda number: f"{number} ({100 * number / n:.1f}%)" if n else f"{number}"
    cell = lambda name, value: "not run".rjust(18) if runs[name] is None else str(value(runs[name])).rjust(18)

    rows += [f"  {'':<54}" + "".join(BPD_RUNS[name].rjust(18) for name in BPD_RUNS),
             f"  {'passed':<54}" + "".join(cell(name, lambda r: pct(sum(x['status'] == 'pass' for x in r))) for name in BPD_RUNS),
             f"  {'    on the first generation (before any trace)':<54}" + "".join(cell(name, lambda r: first_generation([x for x in r if x['status'] == 'pass'])) for name in BPD_RUNS),
             f"  {'    after fix attempts':<54}" + "".join(cell(name, lambda r: sum(x['status'] == 'pass' and x['fix_mode_attempt_count'] > 0 for x in r)) for name in BPD_RUNS)]

    rows += ["", f"ALL {total} TASKS, a BPD result replaces the first one on those {n} tasks",
             f"  {'without BPD':<54}{len(passed):>5} / {total:<5}{100 * len(passed) / total:6.1f}%"]
    for name, label in BPD_RUNS.items():
        results = runs[name]
        if results is None:
            rows.append(f"  {label:<54}{'not run':>5}")
        else:
            total_passed = len(passed) + sum(r["status"] == "pass" for r in results)
            rows.append(f"  {label:<54}{total_passed:>5} / {total:<5}{100 * total_passed / total:6.1f}%")

    notes = [f"{name}: {len(runs[name])} of {n} tasks done (partial)" for name in BPD_RUNS
             if runs[name] is not None and len(runs[name]) < n]
    rows += [""] + notes + ["Note: a BPD run asks the model again, a new sample at temperature > 0. A pass on the first generation",
                            "happens before any trace is used, it shows how much the result moves by sampling alone."]
    return "\n".join(rows)


def save_report(model_name: str, output_dir: str) -> str:
    """Build the report, save it in output_dir and return it."""
    report = build_report(model_name, output_dir)
    with open(os.path.join(output_dir, f"{model_name.replace('/', '_')}_bcb_report.txt"), "w") as report_file:
        report_file.write(report + "\n")
    return report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    print(save_report(model_name = sys.argv[2], output_dir = sys.argv[1]))
