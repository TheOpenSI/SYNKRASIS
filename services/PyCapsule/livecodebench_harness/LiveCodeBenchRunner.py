import json
import os
import subprocess
import sys

class LiveCodeBenchRunner():
    def __init__(self,
                 solution_path: str = None,
                 per_test_timeout: int = 60) -> None:
        self.cwd = os.path.dirname(os.path.abspath(__file__))
        self.PER_TEST_TIMEOUT = per_test_timeout
        self.solution_path = solution_path or os.path.join(self.cwd, "solution.py")


    def run_tests(self, tests: list[dict], entrypoint: str):
        test_type = self._get_test_type(tests)
        if test_type == "functional":
            self._build_functional_file(entrypoint)
        results = self._run_all_tests(tests)

        return results


    def _run_all_tests(self, tests: list[dict]) -> list[dict]:
        results = []
        _failed_count = 0

        for index, test_dict in enumerate(tests):
            try:
                status, detail = self._run_test(test_dict)

            except subprocess.TimeoutExpired:
                status, detail = "timeout", f"Exceeded per-test timeout of {self.PER_TEST_TIMEOUT}s"

            if status != "pass":
                _failed_count += 1

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
            print(f"{_failed_count} tests failed:")
            for result in results:
                if result["status"] != "pass":
                    print(f"Test {result['index']} failed: {result['status']}.\nDetail: {result['detail']}")

        return results


    def _run_test(self, 
                  test_dict: dict) -> tuple[str, str]:
        test_input, expected_output = self._get_test_case(test_dict)
        file_to_run = (self.solution_path.replace('.py', '_test.py') 
                       if self._get_test_type(test_dict) == "functional" 
                       else self.solution_path)
        proc = subprocess.run(
            [sys.executable, file_to_run],
            input = test_input,
            capture_output = True,
            text = True,
            timeout = self.PER_TEST_TIMEOUT,
            cwd = self.cwd
        )
        if proc.returncode != 0:
            return "runtime_error", proc.stderr
 
        if self._get_test_type(test_dict) == "functional":
            return self._check_functional(proc.stdout, expected_output)
        return self._check_stdin(proc.stdout, expected_output)


    def _check_functional(self, stdout: str, expected_output: str) -> tuple[str, str]:
        try:
            actual = json.loads(stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            return "bad_output", f"could not parse stdout: {stdout!r}"
 
        expected = json.loads(expected_output)
        if actual == expected:
            return "pass", ""
        return "AssertionError", f"expected {expected!r}, got {actual!r}"
 
 
    def _check_stdin(self, stdout: str, expected_output: str) -> tuple[str, str]:
        if stdout.split() == expected_output.split():
            return "pass", ""
        return ("AssertionError",
                f"expected {expected_output.split()!r}, got {stdout.split()!r}")


    def _get_test_case(self, test_dict: dict) -> tuple[str, str]:
        return test_dict["input"], test_dict["output"]


    def _build_functional_file(self, entrypoint: str) -> None:
        with open(self.solution_path, "r") as f:
            llm_generated_code = f.read()

        main_block = (
            "\n\n"
            "if __name__ == '__main__':\n"
            "    import json, sys\n"
            "    _args = [json.loads(line) for line in sys.stdin.read().splitlines()]\n"
            f"    _result = Solution().{entrypoint}(*_args)\n"
            "    print(json.dumps(_result))\n"
        )

        _code = "from typing import *\n\n" + llm_generated_code + main_block

        test_file_path = f"{self.solution_path.replace('.py', '')}_test.py"
        with open(test_file_path, "w") as f:
            f.write(_code)


    def _get_test_type(self, tests: list[dict] | dict) -> None:
        return tests[0]["testtype"] if isinstance(tests, list) else tests["testtype"]

if __name__ == "__main__":
    with open("services/PyCapsule/livecodebench_harness/tests.json", "r") as f:
        tests = json.dumps(json.load(f))
    tests = json.loads(tests)
    lcb = LiveCodeBenchRunner(solution_path = "/root/workspace/SYNKRASIS/services/PyCapsule/livecodebench_harness/solution.py")
    lcb.run_tests(tests, "factorial")