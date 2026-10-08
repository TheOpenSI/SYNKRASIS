# =============================================================================================
# LiveCodeBench harness.
#
# main.py (driver) runs solution.py once per test case as a separate process,
# feeds the test input on stdin and compares stdout with the expected output.
# Public tests first (detailed errors), then, only if all public tests pass, the private tests from
# private_tests.json in the same folder (no details are ever printed for them).
# Exit codes: 0 = all passed, 1 = public test failed (single "<ErrorType>: <message>" style error
# on stderr so the PyCapsule error handling can build the fix mode query from it),
# 2 = public passed but a private test failed (stderr: "PRIVATE_TEST_FAILED: <category>").
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
# - classify_response(response: CompletedProcess) -> str
#       "pass" | "private_fail" | "public_fail" from the driver exit code and stdout.
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import json
import re

from modules.ExampleCallDetection import ExampleCallDetection
from utils.code_parsing.code_parser import parse_response


class LCBHarness():
    CLASS_NAME = "Solution"
    SOLUTION_FILE_NAME = "solution.py"
    PRIVATE_TESTS_FILE_NAME = "private_tests.json"
    PUBLIC_PASSED_MARKER = "PUBLIC_TESTS_PASSED_MARKER"
    PRIVATE_FAILED_PREFIX = "PRIVATE_TEST_FAILED:"
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


    def build_driver_content(self, tests: list[dict], per_test_timeout: int = 10) -> str:
        # repr of the json text is a safe python literal.
        return (self._DRIVER_TEMPLATE
                .replace("__SOLUTION_FILE__", repr(self.SOLUTION_FILE_NAME))
                .replace("__PRIVATE_FILE__", repr(self.PRIVATE_TESTS_FILE_NAME))
                .replace("__PUBLIC_MARKER__", repr(self.PUBLIC_PASSED_MARKER))
                .replace("__PRIVATE_PREFIX__", repr(self.PRIVATE_FAILED_PREFIX))
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


# Public tests, detailed errors.
for _index, _test in enumerate(_TESTS):
    _status, _proc = _run_test(_test)
    if _status == "timeout":
        _fail(f"Failed on test case {_index + 1}. Input: {_short(_test['input'])!r}\n"
              f"Exception: Generated code is running infinite loop (exceeded {_TIMEOUT}s).")
    if _status == "runtime_error":
        # The last line of the child's stderr is the error type and message.
        _fail(f"Failed on test case {_index + 1}. Input: {_short(_test['input'])!r}\n" + _proc.stderr[-2000:])
    if _status == "wrong_answer":
        _fail(f"AssertionError: wrong answer on test case {_index + 1}. "
              f"Input: {_short(_test['input'])!r}, "
              f"expected output: {_short(_test['output'])!r}, "
              f"your output: {_short(_proc.stdout)!r}")

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
