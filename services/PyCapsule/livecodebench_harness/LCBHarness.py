# =============================================================================================
# LiveCodeBench harness.
#
# main.py (driver) runs solution.py once per test case as a separate process,
# feeds the test input on stdin and compares stdout with the expected output.
# ALL public tests run first. If any of them fails the driver prints one line to stderr,
# "PUBLIC_RESULTS <json list>", with the result of every public test (pass, wrong_answer, runtime_error, timeout,
# plus input, expected output and what the program printed or its error), and exits with 1.
# Only if all public tests pass the private tests from private_tests.json in the same folder run
# (no details are ever printed for them).
# Exit codes: 0 = all passed, 1 = a public test failed, 2 = public passed but a private test failed
# (stderr: "PRIVATE_TEST_FAILED: <category>").
# Stdout contains PUBLIC_TESTS_PASSED_MARKER once the public tests pass, use it with exit code 2,
# python itself exits with 2 on some launch errors.
#
# Usage:
# - extract_code(response: str) -> str
#       Code from the raw LLM response (parse_response + a repeated code fence fallback).
# - build_solution_content(user_query: dict, llm_generated_code: str) -> str
#       Content of solution.py, dispatches on user_query["test_type"].
# - build_functional_content(user_query: dict, llm_generated_code: str) -> str
#       Starter code (class Solution) problems, args are read from stdin, one json per line.
# - build_stdin_content(llm_generated_code: str) -> str
#       Standard input problems, the code is the program.
# - build_driver_content(tests: list[dict], per_test_timeout: int) -> str
#       Content of main.py, public tests are embedded, no imports from the repo are needed.
# - parse_public_results(stderr: str) -> Optional[list[dict]]
#       The per test results of a failed public run, None if stderr has no such line.
# - classify_response(response: CompletedProcess) -> str
#       "pass" | "private_fail" | "public_fail" from the driver exit code and stdout.
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import json
import re
from typing import Optional

from modules.ExampleCallDetection import ExampleCallDetection
from utils.code_parsing.code_parser import parse_response


class LCBHarness():
    CLASS_NAME = "Solution"
    SOLUTION_FILE_NAME = "solution.py"
    PRIVATE_TESTS_FILE_NAME = "private_tests.json"
    PUBLIC_PASSED_MARKER = "PUBLIC_TESTS_PASSED_MARKER"
    PRIVATE_FAILED_PREFIX = "PRIVATE_TEST_FAILED:"
    PUBLIC_RESULTS_PREFIX = "PUBLIC_RESULTS "
    PRELUDE = "from typing import *\n\n"

    def __init__(self) -> None:
        self.example_call_detection = ExampleCallDetection()


    def extract_code(self, response: str) -> str:
        """
        parse_response, plus a fallback for a repeated code fence, e.g. "### Code\\n```\\n```python\\n...```"
        which parse_response reads as empty code.
        """
        _, code = parse_response(response)
        if code.strip():
            return code
        lines = response.split("### Code")[-1].split("\n")
        fences = [i for i, line in enumerate(lines) if re.match(r"^\s*```", line)]
        if len(fences) < 2:
            return ""
        body = [line for line in lines[fences[0] + 1:fences[-1]] if not re.match(r"^\s*```\w*\s*$", line)]
        return "\n".join(body).strip()


    def build_solution_content(self, user_query: dict, llm_generated_code: str) -> str:
        if user_query["test_type"] == "functional":
            return self.build_functional_content(user_query, llm_generated_code)
        return self.build_stdin_content(llm_generated_code)


    def build_functional_content(self, user_query: dict, llm_generated_code: str) -> str:
        func_name = user_query["entry_point"]
        if not func_name:
            raise ValueError("Functional test type requires an entry_point (func_name in metadata).")

        main_block = (
            "\n\n"
            "if __name__ == '__main__':\n"
            "    import json, sys\n"
            "    _args = [json.loads(line) for line in sys.stdin.read().splitlines()]\n"
            f"    _result = {self.CLASS_NAME}().{func_name}(*_args)\n"
            "    print(json.dumps(_result))\n"
        )

        return self.build_traceable_source(user_query, llm_generated_code) + main_block


    def build_traceable_source(self, user_query: dict, llm_generated_code: str) -> str:
        """
        The solution without the harness main block, example calls removed for functional problems.
        This is what the BPD tracer runs.
        """
        code = llm_generated_code
        if user_query["test_type"] == "functional":
            code = self.example_call_detection.remove_example_calls(code, self.CLASS_NAME)
        return self._add_prelude(code)


    def build_stdin_content(self, llm_generated_code: str) -> str:
        # The code is the program, example call removal does not apply here.
        return self._add_prelude(llm_generated_code)


    def _add_prelude(self, code: str) -> str:
        """
        Prepend the typing import, `from __future__` imports must stay on top.
        """
        future_pattern = re.compile(r"^from __future__ import .*$", re.MULTILINE)
        future_imports = future_pattern.findall(code)
        code = future_pattern.sub("", code)
        return "\n".join(future_imports) + ("\n" if future_imports else "") + self.PRELUDE + code


    def classify_response(self, response) -> str:
        if response.returncode == 0:
            return "pass"
        if response.returncode == 2 and self.PUBLIC_PASSED_MARKER in (response.stdout or ""):
            return "private_fail"
        return "public_fail"


    def parse_public_results(self, stderr: str) -> Optional[list[dict]]:
        """[{"n", "status", "input", "expected", "got" (wrong_answer), "error" (runtime_error)}, ...] or None."""
        for line in (stderr or "").splitlines():
            if line.startswith(self.PUBLIC_RESULTS_PREFIX):
                try:
                    return json.loads(line[len(self.PUBLIC_RESULTS_PREFIX):])
                except json.JSONDecodeError:
                    return None
        return None


    def build_driver_content(self, tests: list[dict], per_test_timeout: int = 10) -> str:
        # repr of the json text is a safe python literal.
        return (self._DRIVER_TEMPLATE
                .replace("__SOLUTION_FILE__", repr(self.SOLUTION_FILE_NAME))
                .replace("__PRIVATE_FILE__", repr(self.PRIVATE_TESTS_FILE_NAME))
                .replace("__PUBLIC_MARKER__", repr(self.PUBLIC_PASSED_MARKER))
                .replace("__PRIVATE_PREFIX__", repr(self.PRIVATE_FAILED_PREFIX))
                .replace("__PUBLIC_RESULTS_PREFIX__", repr(self.PUBLIC_RESULTS_PREFIX))
                .replace("__TIMEOUT__", str(int(per_test_timeout)))
                .replace("__TESTS__", repr(json.dumps(tests))))


    _DRIVER_TEMPLATE = r'''
import json
import os
import subprocess
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
_SOLUTION = os.path.join(_DIR, __SOLUTION_FILE__)
_PRIVATE_FILE = os.path.join(_DIR, __PRIVATE_FILE__)
_TIMEOUT = __TIMEOUT__
_TESTS = json.loads(__TESTS__)
_MAX_LEN = 300
_ENV = dict(os.environ, PYTHONWARNINGS="ignore")


def _short(text):
    return text if len(text) <= _MAX_LEN else text[:_MAX_LEN] + "..."


def _fail(message, code=1):
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(code)


def _matches(testtype, stdout, expected):
    if testtype == "functional":
        try:
            actual = json.loads(stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            return False
        return actual == json.loads(expected)
    return stdout.split() == expected.split()


def _run_test(test):
    """Returns (status, proc), status is pass | timeout | runtime_error | wrong_answer."""
    try:
        proc = subprocess.run([sys.executable, _SOLUTION],
                              input=test["input"],
                              capture_output=True,
                              text=True,
                              timeout=_TIMEOUT,
                              env=_ENV)
    except subprocess.TimeoutExpired:
        return "timeout", None
    if proc.returncode != 0:
        return "runtime_error", proc
    if not _matches(test["testtype"], proc.stdout, test["output"]):
        return "wrong_answer", proc
    return "pass", proc


# All public tests, one result each.
_RESULTS = []
for _index, _test in enumerate(_TESTS):
    _status, _proc = _run_test(_test)
    _result = {"n": _index + 1, "status": _status, "input": _short(_test["input"]), "expected": _short(_test["output"])}
    if _status == "wrong_answer":
        _result["got"] = _short(_proc.stdout)
    elif _status == "runtime_error":
        _result["error"] = _proc.stderr[-2000:]       # the last line is the error type and message
    _RESULTS.append(_result)
if any(_r["status"] != "pass" for _r in _RESULTS):
    _fail(__PUBLIC_RESULTS_PREFIX__ + json.dumps(_RESULTS))

print(f"All {len(_TESTS)} public tests passed!")
print(__PUBLIC_MARKER__)

# Private tests, no details are printed, only the failure category goes to stderr.
if os.path.exists(_PRIVATE_FILE):
    with open(_PRIVATE_FILE, "r") as _f:
        _PRIVATE_TESTS = json.load(_f)
    for _test in _PRIVATE_TESTS:
        _status, _ = _run_test(_test)
        if _status != "pass":
            _fail(__PRIVATE_PREFIX__ + " " + _status, code=2)
    print(f"All {len(_PRIVATE_TESTS)} private tests passed!")
'''
