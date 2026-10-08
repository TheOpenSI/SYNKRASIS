"""
BPD - breakpoint debugger for LLM written solutions.

    trace = BPD().trace(code, test_input, entry_point="f", expected="3")      # -> str, or None if it cannot be traced

Runs the solution on ONE test input, records every line that executes, and returns the code that ran with the
runtime values written next to it (see services/BPD/report.py for the format):

    for n in nums:            # 4 iterations; n=1..4
        if is_even(n):        # F,T,F,T
            count += 1        # count=1,2  (iters 2,4)

- code:        the solution as the LLM wrote it. With entry_point it is a LeetCode style `class Solution` and the
               test input has one json value per line (the arguments of Solution().entry_point(...)); without
               entry_point it is a program that reads stdin and prints.
- test_input:  the input of the failing test, taken from the dataset's test case.
- expected:    the expected output of that test (public tests only), added to the last line.
- trace():     runs in a child process with a time and memory limit, because it executes LLM code (a long native
               call or a memory bomb cannot hang or crash the caller). None means no trace; last_error says why.
               With sandbox_image the child process is a throwaway docker container (no network, memory/cpu/process
               limits, this package mounted read-only), so the code never runs on the host. BPD only needs the
               standard library, any image with python 3.9+ works, e.g. the "synkrasis" image.
- trace_in_process() does the same in this process: for debugging with a debugger and for tests.
"""
from __future__ import annotations

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import ast
import contextlib
import io
import json
import subprocess
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from services.BPD.report import TraceConfig, render_within_budget
from services.BPD.structure import CodeStructure
from services.BPD.tracer import TARGET_FILENAME, TraceCollector, TraceLimit

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKER_PATH = os.path.join(PACKAGE_DIR, "worker.py")
SANDBOX_OPTIONS = ["--network", "none", "--memory", "2g", "--cpus", "1", "--pids-limit", "256"]

# Legend for the model that reads a trace, put it before the trace in the feedback.
LEGEND = ("How to read it: only the lines that ran are listed, with the values after `#`. `x=1,2,3` are the values "
          "of x on successive executions of that line, `a..b` a run of consecutive numbers, `T/F` the outcome of a "
          "condition on each execution, `F×3` three equal values, `(iters 2,4)` the loop iterations the line ran in, "
          "`...` omitted middle values. Nested lines belong to the line above.")


class BPD:

    def __init__(self, max_chars: int = 6000, max_steps: int = 20000, max_seconds: float = 5.0, timeout: int = 20,
                 sandbox_image: Optional[str] = None) -> None:
        """
        Args:
            max_chars (int): the trace is shortened (less detail) until it fits.
            max_steps (int): lines executed before the trace is abandoned.
            max_seconds (float): seconds of tracing before it is abandoned.
            timeout (int): seconds before trace() kills its child process (covers one long native call).
            sandbox_image (str): docker image to run trace() in, None = a child process on this machine.
        """
        self.max_chars = max_chars
        self.max_steps = max_steps
        self.max_seconds = max_seconds
        self.timeout = timeout
        self.sandbox_image = sandbox_image
        self.last_error: Optional[str] = None      # why the last call returned None


    def trace(self, code: str, test_input: str, entry_point: Optional[str] = None,
              expected: Optional[str] = None) -> Optional[str]:
        """The trace of code on test_input, run in a child process. None when it cannot be traced (see last_error)."""
        self.last_error = None
        request = {"code": code, "test_input": test_input, "entry_point": entry_point, "expected": expected,
                   "limits": [self.max_chars, self.max_steps, self.max_seconds]}
        command, container_name = self._worker_command()
        try:
            process = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True,
                                     timeout=self.timeout)
            answer = json.loads(process.stdout.strip().splitlines()[-1])
        except subprocess.TimeoutExpired:
            if container_name:                      # killing the docker client does not stop the container
                subprocess.run(["docker", "kill", container_name], capture_output=True)
            self.last_error = "timeout"
            return None
        except (IndexError, json.JSONDecodeError):
            self.last_error = "worker_failed"
            return None
        self.last_error = answer["error"]
        return answer["trace"]

    def _worker_command(self) -> tuple[list[str], Optional[str]]:
        """The command that runs worker.py: here, or in a throwaway container. Returns (command, container name)."""
        if self.sandbox_image is None:
            return [sys.executable, WORKER_PATH], None
        name = f"bpd_{uuid.uuid4().hex[:12]}"
        command = ["docker", "run", "--rm", "-i", "--name", name, *SANDBOX_OPTIONS, "-e", "PYTHONDONTWRITEBYTECODE=1",
                   "-v", f"{PACKAGE_DIR}:/usr/src/services/BPD:ro",
                   "--entrypoint", "python", self.sandbox_image, "/usr/src/services/BPD/worker.py"]
        return command, name

    def trace_in_process(self, code: str, test_input: str, entry_point: Optional[str] = None,
                         expected: Optional[str] = None) -> Optional[str]:
        """Same as trace() in this process. Use trace() for LLM code you do not trust."""
        self.last_error = None
        original_stdin = sys.stdin
        try:
            if entry_point:
                arguments = [json.loads(line) for line in test_input.splitlines()]
                source, expression = code, f"Solution().{entry_point}({', '.join(repr(a) for a in arguments)})"
            else:
                source, expression = hoist_script(code), "__bpd_main__()"
            sys.stdin = io.TextIOWrapper(io.BytesIO(test_input.encode()))
            return self.trace_expression(source, expression, expected, show_output=entry_point is None)
        except TraceLimit:
            self.last_error = "trace_limit"
        except BaseException as exc:                    # syntax error, sys.exit(), bad input ...
            self.last_error = f"{type(exc).__name__}: {exc}"
        finally:
            sys.stdin = original_stdin
        return None

    def trace_expression(self, source: str, expression: str, expected: Optional[str] = None,
                         show_output: bool = False) -> str:
        """
        Lowest level: evaluate `expression` in the namespace of `source` under the tracer, e.g. "f([1, 2, 3])".
        show_output: the last line reports what the code printed instead of what the expression returned.
        Raises TraceLimit when the trace is too long.
        """
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            namespace: dict[str, Any] = {"__name__": "__bpd_target__"}
            exec(compile(source, TARGET_FILENAME, "exec"), namespace)
            structure = CodeStructure(source)
            collector = TraceCollector(TARGET_FILENAME, structure, max_steps=self.max_steps, max_seconds=self.max_seconds)
            code = compile(expression, "<bpd-driver>", "eval")
            result, error, roots = collector.run(lambda: eval(code, namespace))
        return render_within_budget(structure, roots, result, error, expected,
                                    printed.getvalue() if show_output else None, TraceConfig(max_chars=self.max_chars))


def hoist_script(code: str) -> str:
    """
    A stdin program has statements at the top level, which the tracer cannot see (it traces function calls).
    Moves them into a function __bpd_main__() so they can be traced; imports, functions and classes stay where they are,
    the body of `if __name__ == "__main__":` is moved too.
    """
    keep, body = [], []
    for node in ast.parse(code).body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            keep.append(node)
        elif (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
              and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"):
            body.extend(node.body)
        else:
            body.append(node)
    stores = {n.id for stmt in body for n in ast.walk(stmt) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    used_by_functions = {n.id for node in keep if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                         for n in ast.walk(node) if isinstance(n, ast.Name)}
    shared = sorted(stores & used_by_functions)         # only these must stay global; the rest become normal locals
    if shared:
        body.insert(0, ast.Global(names=shared))
    function = ast.FunctionDef(name="__bpd_main__", args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[],
                               kw_defaults=[], defaults=[]), body=body or [ast.Pass()], decorator_list=[], type_params=[])
    return ast.unparse(ast.fix_missing_locations(ast.Module(body=keep + [function], type_ignores=[])))
