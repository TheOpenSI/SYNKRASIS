"""
Trace one LiveCodeBench solution on one input with BPD (concise report).
- trace_request(request) -> result: does the work, in the current process. Handy for debugging, see lcb_trace_demo.py.
- main(): the subprocess entry used by lcb_trace.LCBTracer. It caps memory first, because it executes LLM code.
request: {code, mode: functional|stdin, entry_point, input, expected, max_chars, max_steps, full (optional)}
result:  {ok, report, output, matches, error, steps}
  full=True gives the complete default report (source listing included) instead of the concise one.
  ok=False: the code could not be traced (syntax error, step limit, ...), error says why.
  ok=True and error set: the traced code raised, the report shows where.
Stdin programs have their top level statements moved into __bpd_main__() so the tracer can see them.
"""
import ast
import contextlib
import io
import json
import os
import resource
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from services.BPD.bpd import BreakpointDebugger
from services.BPD.report import ReportConfig
from services.BPD import tracer as tracer_mod


class StepLimit(BaseException):
    pass


_ORIGINAL_ON_LINE = tracer_mod.TraceCollector._on_line


def install_step_cap(max_steps: int):
    """Stops a trace with StepLimit after max_steps executed lines, returns the step counter."""
    counter = {"n": 0}

    def capped(self, frame):
        counter["n"] += 1
        if counter["n"] > max_steps:
            raise StepLimit()
        return _ORIGINAL_ON_LINE(self, frame)

    tracer_mod.TraceCollector._on_line = capped
    return counter


def hoist_script(code: str) -> str:
    """Move top level statements into __bpd_main__() so the trace sees them."""
    tree = ast.parse(code)
    keep, body = [], []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            keep.append(node)
        elif (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
              and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"):
            body.extend(node.body)
        else:
            body.append(node)
    stores = sorted({n.id for stmt in body for n in ast.walk(stmt)
                     if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)})
    if stores:
        body.insert(0, ast.Global(names=stores))
    if not body:
        body = [ast.Pass()]
    func = ast.FunctionDef(name="__bpd_main__", args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[],
                           kw_defaults=[], defaults=[]), body=body, decorator_list=[], type_params=[])
    module = ast.Module(body=keep + [func], type_ignores=[])
    return ast.unparse(ast.fix_missing_locations(module))


def trace_request(req: dict) -> dict:
    counter = install_step_cap(req["max_steps"])
    config = ReportConfig() if req.get("full") else ReportConfig.concise(req["max_chars"])
    debugger = BreakpointDebugger(config)
    out = {"ok": False, "report": "", "output": "", "matches": None, "error": None, "steps": 0}
    captured = io.StringIO()
    original_stdin = sys.stdin
    try:
        if req["mode"] == "functional":
            args = [json.loads(line) for line in req["input"].splitlines()]
            expression = f"Solution().{req['entry_point']}({', '.join(repr(a) for a in args)})"
            source, run = req["code"], lambda s: debugger.run_expression(s, expression)
        else:
            source = hoist_script(req["code"])
            run = lambda s: debugger.run_expression(s, "__bpd_main__()")
        sys.stdin = io.TextIOWrapper(io.BytesIO(req["input"].encode()))
        with contextlib.redirect_stdout(captured):
            report = run(source)
        out["ok"] = True
        out["report"] = report.text
        if req["mode"] == "functional":
            out["output"] = json.dumps(report.result)
            try:
                out["matches"] = (report.exception is None and report.result == json.loads(req["expected"]))
            except Exception:
                out["matches"] = False
        else:
            out["output"] = captured.getvalue()
            out["matches"] = report.exception is None and out["output"].split() == req["expected"].split()
        if report.exception is not None:
            out["error"] = f"{type(report.exception).__name__}: {report.exception}"
    except StepLimit:
        out["error"] = "step_limit"
    except BaseException as exc:  # noqa
        out["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        sys.stdin = original_stdin
    out["steps"] = counter["n"]
    return out


def main():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
    sys.setrecursionlimit(5000)
    print(json.dumps(trace_request(json.load(sys.stdin))))


if __name__ == "__main__":
    main()
