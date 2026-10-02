import json
import os
import subprocess
import sys

class LiveCodeBenchRunner():
    def __init__(self,
                 solution_path: str = None,
                 test_path: str = None,
                 per_test_timeout: int = 60) -> None:
        self.cwd = os.path.dirname(os.path.abspath(__file__))
        self.PER_TEST_TIMEOUT = per_test_timeout
        self.solution_path = solution_path or os.path.join(self.cwd, "solution.py")
        self.test_path = test_path or os.path.join(self.cwd, "tests.json")
        self._load_test_cases()


    def run_tests(self) -> None:
        if self.test_type == "stdin":
            self._run_stdin_tests()

        elif self.test_type == "functional":
            self._run_functional_tests()

        else:
            raise ValueError(f"Unknown test type: {self.test_type}")


    def _run_stdin_tests(self) -> None:
        results = []

        for index, test_dict in enumerate(self.tests):
            try:
                status, detail = self._run_stdin_test(test_dict)

            except subprocess.TimeoutExpired:
                status, detail = "timeout", f"exceeded per-test timeout of {self.PER_TEST_TIMEOUT}s"

            results.append(
                {
                    "index": index,
                    "status": status,
                    "detail": detail
                }
            )
        if all(result["status"] == "pass" for result in results):
            print("All tests passed!")
        else:
            print("Some tests failed:")
            for result in results:
                if result["status"] != "pass":
                    print(f"Test {result['index']} failed: {result['status']}. Detail: {result['detail']}")


    def _run_stdin_test(self, test_dict: dict):
        test_input, expected_output = self._get_test_case(test_dict)
        proc = subprocess.run(
            [sys.executable, self.solution_path],
            input = test_input,
            capture_output = True,
            text = True,
            timeout = self.PER_TEST_TIMEOUT,
            cwd = self.cwd
        )
        if proc.returncode == 0:
            actual_output = proc.stdout
            if actual_output.split() == expected_output.split():
                return "pass", ""
            else:
                return ("AssertionError", 
                        f"expected {expected_output.split()!r}, got {actual_output.split()!r}")
        else:
            return "runtime_error", proc.stderr


    def _run_functional_tests(self) -> None:
        pass


    def _run_functional_test(self) -> None:
        pass


    def _load_test_cases(self) -> None:
        with open(self.test_path) as f:
            test_cases = json.load(f)
        self.test_type = test_cases["test_type"]
        self.func_name = test_cases.get("func_name")
        self.tests = test_cases["tests"]


    def _get_test_case(self, test_dict: dict) -> tuple[str, str]:
        return test_dict["input"], test_dict["output"]


# def run_functional_test(test, func_name):
#     """Run harness_functional.py, which imports solution.py and calls the method."""
#     proc = subprocess.run(
#         [sys.executable, "harness_functional.py", func_name],
#         input=test["input"],
#         capture_output=True,
#         text=True,
#         timeout=PER_TEST_TIMEOUT,
#         cwd=HERE,
#     )
#     if proc.returncode != 0:
#         return "runtime_error", os.truncate(proc.stderr)

#     # Only trust the line that starts with the sentinel; anything else the
#     # solution printed is ignored.
#     result_line = None
#     for line in proc.stdout.splitlines():
#         if line.startswith(SENTINEL):
#             result_line = line[len(SENTINEL):]
#     if result_line is None:
#         return "runtime_error", "harness produced no result"

#     actual = json.loads(result_line)
#     expected = json.loads(test["output"])
#     if actual == expected:
#         return "pass", ""
#     return "wrong_answer", f"expected {expected!r}, got {actual!r}"


# def main():
#     started = time.time()

#     for index, test in enumerate(spec["tests"]):
#         # Per-problem budget: stop early and mark the rest as not run.
#         if time.time() - started > TOTAL_BUDGET:
#             results.append({"index": index, "status": "not_run", "seconds": 0.0, "detail": ""})
#             continue

#         t0 = time.time()
#         try:
#             if test_type == "stdin":
#                 status, detail = run_stdin_test(test)
#             else:
#                 status, detail = run_functional_test(test, func_name)
#         except subprocess.TimeoutExpired:
#             status, detail = "timeout", f"exceeded {PER_TEST_TIMEOUT}s"
#         results.append({
#             "index": index,
#             "status": status,
#             "seconds": round(time.time() - t0, 3),
#             "detail": detail,
#         })

#     summary = {
#         "test_type": test_type,
#         "all_passed": all(r["status"] == "pass" for r in results),
#         "passed": sum(r["status"] == "pass" for r in results),
#         "total": len(results),
#         "results": results,
#     }
#     with open(os.path.join(HERE, "results.json"), "w") as f:
#         json.dump(summary, f, indent=2)

#     # A short human-readable line; the host should read results.json instead.
#     print(f"{summary['passed']}/{summary['total']} passed")


if __name__ == "__main__":
    lcb = LiveCodeBenchRunner()
    lcb.run_tests()