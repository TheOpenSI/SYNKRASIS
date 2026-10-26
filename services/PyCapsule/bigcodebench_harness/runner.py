"""
Runs the unit tests of a BigCodeBench task one by one, in this process (standard library only, it runs in the container).

    python runner.py <candidate.py> <results.jsonl> <seconds per test> [first test index]

candidate.py is the code of the LLM followed by the test code of the task. It is loaded as the module "candidate".
Every test method of every TestCase class of the module runs on its own (setUp, tearDown and decorators as usual),
in the order unittest.main would use: classes in the order they are defined, methods sorted by name.
results.jsonl gets one json line per finished test, flushed at once, so the lines are there even if the process dies:
    {"tests": ["TestCases.test_case_1", ...]}                       first line, the tests that will run
    {"index": 0, "status": "pass" | "fail" | "error", "message": "traceback"}
fail = an assertion of the test failed (a wrong answer), error = any other exception, also the time limit.
If the candidate cannot be loaded (syntax error, import error ...) the first line is {"load_error": "traceback"}.
"""
import json
import signal
import sys
import traceback
import types
import unittest


class TestTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise TestTimeout("the test took longer than the time limit")


def load_module(candidate_path: str) -> types.ModuleType:
    module = types.ModuleType("candidate")
    module.__file__ = candidate_path
    sys.modules["candidate"] = module
    with open(candidate_path, "r") as candidate_file:
        source = candidate_file.read()
    exec(compile(source, candidate_path, "exec"), module.__dict__)
    return module


def list_tests(module: types.ModuleType) -> list[tuple[type, str]]:
    classes = [value for value in vars(module).values()
               if isinstance(value, type) and issubclass(value, unittest.TestCase) and value.__module__ == module.__name__]
    return [(cls, name) for cls in classes for name in unittest.TestLoader().getTestCaseNames(cls)]


def run_test(cls: type, name: str, seconds: int) -> dict:
    result = unittest.TestResult()
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        cls(name).run(result)
    except BaseException:                   # also what unittest does not catch (SystemExit, KeyboardInterrupt ...)
        return {"status": "error", "message": traceback.format_exc()}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    if result.failures:
        return {"status": "fail", "message": result.failures[0][1]}
    if result.errors:
        return {"status": "error", "message": result.errors[0][1]}
    return {"status": "pass", "message": ""}


def main() -> None:
    candidate_path, results_path, seconds = sys.argv[1], sys.argv[2], int(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    with open(results_path, "a") as results_file:
        def write(record: dict) -> None:
            results_file.write(json.dumps(record) + "\n")
            results_file.flush()

        try:
            module = load_module(candidate_path)
        except BaseException:
            write({"load_error": traceback.format_exc()})
            return
        tests = list_tests(module)
        if first == 0:
            write({"tests": [f"{cls.__name__}.{name}" for cls, name in tests]})
        for index, (cls, name) in enumerate(tests):
            if index >= first:
                write({"index": index, **run_test(cls, name, seconds)})


if __name__ == "__main__":
    main()
