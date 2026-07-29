import pandas as pd
import json, os, glob

from pathlib import Path
from collections import defaultdict


class ExperimentAnalyser:
    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)
        self.data: pd.DataFrame = self._load_data()
        self.error_df: pd.DataFrame = self._preprocess_data()


    def analyse(self) -> None:
        self._check_accuracy()
        # self._check_fix_mode_distribution()
        self._check_error_frequency()
        # self._check_error_persistence()
        # self._check_turnaround_rate()
        # self._check_per_test_evolution()

    def _check_accuracy(self) -> None:
        """
        Overall pass/fail accuracy, plus first-attempt and fix-mode pass rates.
        """
        if "status" not in self.data.columns:
            raise ValueError("The required column 'status' is missing in the data.")

        total_cases   = len(self.data)
        passed_cases  = len(self.data[self.data["status"] == "pass"])
        failed_cases  = total_cases - passed_cases
        accuracy      = passed_cases / total_cases if total_cases > 0 else 0

        first_attempt = len(self.data[
            (self.data["status"] == "pass") &
            (self.data["fix_mode_attempt_count"] == 0)
        ])
        fixed_passes  = passed_cases - first_attempt

        print("=" * 55)
        print("ACCURACY")
        print("=" * 55)
        print(f"  Total tasks          : {total_cases}")
        print(f"  Passed               : {passed_cases}  ({accuracy:.2%})")
        print(f"  Failed               : {failed_cases}  ({1 - accuracy:.2%})")
        print(f"  Passed first attempt : {first_attempt}  ({first_attempt/total_cases:.2%})")
        print(f"  Passed after fixing  : {fixed_passes}  ({fixed_passes/total_cases:.2%})")
        print()


    def _check_fix_mode_distribution(self) -> None:
        """
        Distribution of how many fix attempts were needed,
        broken down by final status.
        """
        print("=" * 55)
        print("FIX-MODE ATTEMPT DISTRIBUTION")
        print("=" * 55)

        dist = (
            self.data
            .groupby(["fix_mode_attempt_count", "status"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )

        for _, row in dist.iterrows():
            attempts = int(row["fix_mode_attempt_count"])
            passed   = int(row.get("pass", 0))
            failed   = int(row.get("fail", 0))
            total    = passed + failed
            label    = f"  {attempts} fix attempt(s)"
            print(f"{label:<25}: {total:>4} tasks  |  pass: {passed:>4}  fail: {failed:>4}")
        print()


    def _check_error_frequency(self) -> None:
        """
        Frequency of each error type across all tasks and attempts,
        split by the task's final status.
        """
        if self.error_df.empty:
            print("No errors recorded.\n")
            return

        print("=" * 55)
        print("ERROR TYPE FREQUENCY")
        print("=" * 55)

        freq = (
            self.error_df
            .groupby(["error_type", "final_status"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        freq["total"] = freq.get("pass", 0) + freq.get("fail", 0)
        freq = freq.sort_values("total", ascending=False)

        total_errors = freq["total"].sum()
        print(f"  Total error occurrences: {total_errors}\n")
        print(f"  {'Error Type':<45} {'Total':>6}  {'Pass':>6}  {'Fail':>6}")
        print(f"  {'-'*45} {'-'*6}  {'-'*6}  {'-'*6}")

        for _, row in freq.iterrows():
            passed = int(row.get("pass", 0))
            failed = int(row.get("fail", 0))
            print(f"  {row['error_type']:<45} {int(row['total']):>6}  {passed:>6}  {failed:>6}")
        print()


    def _check_error_persistence(self) -> None:
        """
        For tasks that used all 5 fix attempts, measure how frozen
        the error pattern was across attempts.

        Persistence score: average Jaccard similarity between consecutive
        attempt error sets. Score of 1.0 means completely frozen.
        """
        print("=" * 55)
        print("ERROR PERSISTENCE (failed tasks, all 5 attempts used)")
        print("=" * 55)

        max_attempts = self.data["fix_mode_attempt_count"].max()
        exhausted    = self.data[self.data["fix_mode_attempt_count"] == max_attempts]

        frozen_count   = 0
        evolving_count = 0
        scores         = []

        for _, row in exhausted.iterrows():
            trace = row["error_trace"]
            if len(trace) < 2:
                continue

            attempt_sets   = [set(attempt) for attempt in trace]
            similarities   = []

            for i in range(len(attempt_sets) - 1):
                a, b       = attempt_sets[i], attempt_sets[i + 1]
                union      = a | b
                jaccard    = len(a & b) / len(union) if union else 1.0
                similarities.append(jaccard)

            avg_sim = sum(similarities) / len(similarities)
            scores.append(avg_sim)

            if avg_sim == 1.0:
                frozen_count += 1
            else:
                evolving_count += 1

        overall_avg = sum(scores) / len(scores) if scores else 0.0

        print(f"  Tasks that exhausted all attempts : {len(exhausted)}")
        print(f"  Completely frozen error pattern   : {frozen_count}")
        print(f"  Evolving error pattern            : {evolving_count}")
        # print(f"  Average persistence score (0-1)   : {overall_avg:.3f}")
        # print(f"  (1.0 = same errors every attempt, 0.0 = completely different)\n")


    def _check_turnaround_rate(self) -> None:
        """
        For each error type, how often did the LLM recover from it
        by the next attempt?

        Recovery is defined per test position: if a test at position P
        had error E at attempt N, did that same position show no error
        (or a different error) at attempt N+1?
        """
        print("=" * 55)
        print("TURNAROUND RATE BY ERROR TYPE")
        print("=" * 55)

        if self.error_df.empty:
            print("  No errors recorded.\n")
            return

        # Build lookup: (task_id, attempt_number, test_position) -> error_type
        lookup = (
            self.error_df
            .set_index(["task_id", "attempt_number", "test_position"])["error_type"]
            .to_dict()
        )

        resolved   = defaultdict(int)
        unresolved = defaultdict(int)

        for (task_id, attempt_number, test_position), error_type in lookup.items():
            next_key = (task_id, attempt_number + 1, test_position)
            if next_key in lookup:
                # Position still has an error next attempt
                unresolved[error_type] += 1
            else:
                # Position either passed or task ended — counts as resolved
                resolved[error_type] += 1

        all_types = set(resolved) | set(unresolved)
        rows = []
        for error_type in all_types:
            r = resolved[error_type]
            u = unresolved[error_type]
            total = r + u
            rate  = r / total if total > 0 else 0.0
            rows.append((error_type, total, r, u, rate))

        rows.sort(key=lambda x: x[0])  # alphabetical for readability

        print(f"  {'Error Type':<45} {'Total':>6}  {'Resolved':>9}  {'Stuck':>6}  {'Recovery%':>10}")
        print(f"  {'-'*45} {'-'*6}  {'-'*9}  {'-'*6}  {'-'*10}")

        for error_type, total, r, u, rate in rows:
            print(f"  {error_type:<45} {total:>6}  {r:>9}  {u:>6}  {rate:>9.1%}")
        print()


    def _check_per_test_evolution(self) -> None:
        """
        Since test order is consistent across attempts, track how
        individual test positions evolve across attempts for failed tasks.

        Reports:
          - How many test positions never changed error type (fully stuck)
          - How many cycled between different errors (confused)
          - How many were resolved mid-run but then regressed
        """
        print("=" * 55)
        print("PER-TEST POSITION EVOLUTION (failed tasks only)")
        print("=" * 55)

        failed_errors = self.error_df[self.error_df["final_status"] == "fail"]

        if failed_errors.empty:
            print("  No failed task errors recorded.\n")
            return

        stuck      = 0
        cycling    = 0
        regressed  = 0
        total_pos  = 0

        grouped = failed_errors.groupby(["task_id", "test_position"])

        for (task_id, test_position), group in grouped:
            errors_over_attempts = group.sort_values("attempt_number")["error_type"].tolist()
            total_pos += 1

            unique_errors = set(errors_over_attempts)

            if len(unique_errors) == 1:
                stuck += 1
            else:
                cycling += 1

        # Regression: a position had no error in an intermediate attempt
        # then reappeared — requires cross-referencing with pass positions
        # We detect this by checking if attempt numbers are non-contiguous
        # for a given (task_id, test_position)
        all_failed_tasks = self.data[self.data["status"] == "fail"]

        for _, row in all_failed_tasks.iterrows():
            trace      = row["error_trace"]
            n_attempts = len(trace)
            if n_attempts < 3:
                continue

            # For each test position, collect which attempts had an error
            pos_attempts = defaultdict(set)
            for attempt_num, attempt_errors in enumerate(trace):
                for pos, _ in enumerate(attempt_errors):
                    pos_attempts[pos].add(attempt_num)

            for pos, attempt_set in pos_attempts.items():
                sorted_attempts = sorted(attempt_set)
                # If there's a gap then a reappearance, it regressed
                if sorted_attempts != list(range(sorted_attempts[0], sorted_attempts[-1] + 1)):
                    regressed += 1

        print(f"  Total test positions tracked    : {total_pos}")
        print(f"  Fully stuck (same error always) : {stuck}  ({stuck/total_pos:.2%})")
        print(f"  Cycling (error type changed)    : {cycling}  ({cycling/total_pos:.2%})")
        print(f"  Regressed (cleared then returned): {regressed}")
        print()


    def _preprocess_data(self) -> pd.DataFrame:
        """
        Explode the nested error_trace into a long-form DataFrame.
        Each row represents a single error occurrence with its task,
        attempt number, test position, and final task status.
        """
        if "error_trace" not in self.data.columns:
            raise ValueError("The required column 'error_trace' is missing in the data.")

        records = []

        for _, row in self.data.iterrows():
            for attempt_number, attempt_errors in enumerate(row["error_trace"]):
                for test_position, error_type in enumerate(attempt_errors):
                    records.append({
                        "task_id"       : row["task_id"],
                        "attempt_number": attempt_number,
                        "test_position" : test_position,
                        "error_type"    : error_type,
                        "final_status"  : row["status"]
                    })

        return pd.DataFrame(records)


    def _load_data(self) -> pd.DataFrame:
        file_extension = self.file_path.suffix
        if file_extension == ".json":
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            return pd.DataFrame(data)

        elif file_extension == ".csv":
            return pd.read_csv(self.file_path)

        else:
            raise ValueError(f"Unsupported file format: {file_extension}")


if __name__ == "__main__":
    def get_json_files_in_current_dir() -> list[str]:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return glob.glob(os.path.join(current_dir, "*.json"))
    paths = get_json_files_in_current_dir()
    for p in paths:
        if "humaneval" in p.lower() or "bigcodebench" in p.lower():
            continue
        print("#"*55)
        print(Path(p).stem)
        print("#"*55)
        analyser = ExperimentAnalyser(file_path = p)
        analyser.analyse()
