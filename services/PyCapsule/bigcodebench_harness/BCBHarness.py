# =============================================================================================
# BigCodeBench harness.
#
# A task has the code of the LLM and a unittest TestCase class. Every attempt writes these files into the mount directory:
#   main.py          the driver (driver_template.txt), runs the tests and prints the result of every test
#   runner.py        runs the test methods one by one (runner.py), copied from here
#   solution.py      the code of the LLM (example calls removed)
#   tests.py         the test code of the task
#   candidate.py     solution.py + tests.py, this is what the runner loads
#   bpd/             the BPD package, the driver uses it to trace failed tests
# The driver prints two lines to stderr and exits with 0 only if every test passed:
#   TEST_RESULTS <json list>   one string per test: "pass", "FAIL: <test>\n<traceback>" (a failed assertion, a wrong
#                              answer) or "ERROR: <test>\n<traceback>" (any other exception, the time limit ...)
#   TEST_TRACES <json dict>    test index -> BPD trace, only for failed tests and at most max_traces of them
#
# Usage:
# - test_names(test_code: str) -> list[str]
#       The test methods as "Class.method", in the order of the runner.
# - build_solution_content(llm_generated_code: str) -> str
# - build_candidate_content(solution_content: str, test_code: str) -> str
# - build_driver_content(test_code: str, per_test_timeout: int, max_traces: Optional[int], total_timeout: int) -> str
# - copy_support_files(mount_dir: str) -> None
#       runner.py and the BPD package into the mount directory.
# - parse_test_results(stderr: str) -> Optional[list[str]]
# - parse_traces(stderr: str) -> dict[int, str]
# - is_wrong_answer(result: str) -> bool
# - concise_results(results: list[str]) -> tuple[list[str], list[str]]
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import ast
import json
import shutil
from typing import Optional

from modules.ErrorHandling import ErrorHandling
from modules.ExampleCallDetection import ExampleCallDetection


class BCBHarness():

    def __init__(self) -> None:
        self.example_call_detection = ExampleCallDetection()
        self.PASS = "pass"
        self.RESULTS_PREFIX = "TEST_RESULTS "
        self.TRACES_PREFIX = "TEST_TRACES "
        self._DIR = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(self._DIR, "driver_template.txt"), "r") as template_file:
            self._DRIVER_TEMPLATE = template_file.read()
        self.error_handling = ErrorHandling(target_file_name = "/usr/src/app/candidate.py")


    def test_names(self, test_code: str) -> list[str]:
        """
        The test methods as "Class.method". Same rule as unittest and runner.py: the classes in the order they are 
        defined, the methods that start with "test" sorted by name.
        """
        names = []
        for node in ast.parse(test_code).body:
            if isinstance(node, ast.ClassDef) and any(ast.unparse(base).endswith("TestCase") for base in node.bases):
                names += [f"{node.name}.{method}" for method in sorted(set(     # a method defined twice is one test
                    item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name.startswith("test")))]
        return names


    def build_solution_content(self, llm_generated_code: str) -> str:
        return self.example_call_detection.extract_code_blocks(llm_generated_code)


    def build_candidate_content(self, solution_content: str, test_code: str) -> str:
        return solution_content + "\n\n" + test_code


    def build_driver_content(self, test_code: str, per_test_timeout: int = 30, max_traces: Optional[int] = 0,
                             total_timeout: int = 300) -> str:
        return (self._DRIVER_TEMPLATE
                .replace("__TEST_NAMES__", repr(json.dumps(self.test_names(test_code))))
                .replace("__TOTAL_TIMEOUT__", str(int(total_timeout)))
                .replace("__TIMEOUT__", str(int(per_test_timeout)))
                .replace("__MAX_TRACES__", repr(max_traces)))


    def copy_support_files(self, mount_dir: str) -> None:
        shutil.copy(os.path.join(self._DIR, "runner.py"), os.path.join(mount_dir, "runner.py"))
        destination = os.path.join(mount_dir, "bpd", "services", "BPD")
        os.makedirs(destination, exist_ok = True)
        bpd_dir = os.path.join(self._DIR, "..", "..", "BPD")
        for file_name in os.listdir(bpd_dir):
            if file_name.endswith(".py"):
                shutil.copy(os.path.join(bpd_dir, file_name), os.path.join(destination, file_name))


    def parse_test_results(self, stderr: str) -> Optional[list[str]]:
        """One string per test, None if the driver did not print them."""
        for line in (stderr or "").splitlines():
            if line.startswith(self.RESULTS_PREFIX):
                try:
                    return json.loads(line[len(self.RESULTS_PREFIX):])
                except json.JSONDecodeError:
                    return None
        return None


    def parse_traces(self, stderr: str) -> dict[int, str]:
        """Test index -> trace."""
        for line in (stderr or "").splitlines():
            if line.startswith(self.TRACES_PREFIX):
                try:
                    return {int(index): trace for index, trace in json.loads(line[len(self.TRACES_PREFIX):]).items()}
                except json.JSONDecodeError:
                    return {}
        return {}


    def is_wrong_answer(self, result: str) -> bool:
        """A failed assertion of the test: unittest calls it a failure, any other exception is an error."""
        return result.startswith("FAIL: ")


    def concise_results(self, results: list[str]) -> tuple[list[str], list[str]]:
        """
        The error message of every failed test made concise with ErrorHandling, passed tests stay as they are.

        Returns:
            tuple: the messages (same length and order as results) and the error types of the failed tests only.
        """
        messages, error_types = [], []
        for result in results:
            if result == self.PASS:
                messages.append(result)
                continue
            messages.append(self.error_handling(result))
            error_types.extend(self.error_handling.current_error_type)
        return messages, error_types
