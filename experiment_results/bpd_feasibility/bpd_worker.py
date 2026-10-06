"""
Experiment worker: trace one LiveCodeBench solution on one input with BPD.
stdin (json): {code, mode: functional|stdin, entry_point, input, expected, include_source, max_steps}
stdout (json): {ok, report, output, matches, error, steps}
Run in a subprocess by the caller (timeout, memory cap).
"""
import ast
import contextlib
import io
import json
import resource
import sys

sys.path.insert(0, "/home/ad/workspace/SYNKRASIS")
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
sys.setrecursionlimit(5000)

from services.BPD.bpd import BreakpointDebugger
from services.BPD.report import ReportConfig
from services.BPD import tracer as tracer_mod


class StepLimit(BaseException):
    pass


def install_step_cap(max_steps: int):
    counter = {"n": 0}
    original = tracer_mod.TraceCollector._on_line

    def capped(self, frame):
        counter["n"] += 1
        if counter["n"] > max_steps:
            raise StepLimit()
        return original(self, frame)

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


def main():
    req = json.load(sys.stdin)
    counter = install_step_cap(req["max_steps"])
    config = ReportConfig(include_source=req["include_source"])
    debugger = BreakpointDebugger(config)
    out = {"ok": False, "report": "", "output": "", "matches": None, "error": None, "steps": 0}
    captured = io.StringIO()
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
    out["steps"] = counter["n"]
    sys.stdout = sys.__stdout__
    print(json.dumps(out))


if __name__ == "__main__":
    main()
