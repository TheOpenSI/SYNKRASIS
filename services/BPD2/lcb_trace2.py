"""
Compact trace of an LLM solution on one LiveCodeBench test (in this process, see
services/BPD/lcb_trace_worker.py for the subprocess + memory cap wrapper the pipeline uses).

    result = trace_request({"code": source, "mode": "functional" | "stdin", "entry_point": "f",
                            "input": "...", "expected": "...", "max_steps": 300000})
    result = {ok, report, output, matches, error, steps}
Stdin programs get their top level statements moved into __bpd_main__() (hoist_script), the report hides that wrapper.
"""
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import contextlib
import io
import json

from services.BPD.lcb_trace_worker import hoist_script
from services.BPD2.bpd2 import CompactDebugger
from services.BPD2.compact_report import CompactConfig
from services.BPD2.fast_tracer import TraceLimit


def trace_request(req: dict, config: CompactConfig = None) -> dict:
    debugger = CompactDebugger(max_steps=req["max_steps"], max_seconds=req.get("max_seconds", 5.0))
    out = {"ok": False, "report": "", "output": "", "matches": None, "error": None, "steps": 0}
    captured = io.StringIO()
    original_stdin = sys.stdin
    try:
        if req["mode"] == "functional":
            args = [json.loads(line) for line in req["input"].splitlines()]
            expression = f"Solution().{req['entry_point']}({', '.join(repr(a) for a in args)})"
            source = req["code"]
        else:
            source, expression = hoist_script(req["code"]), "__bpd_main__()"
        sys.stdin = io.TextIOWrapper(io.BytesIO(req["input"].encode()))
        with contextlib.redirect_stdout(captured):
            trace = debugger.run_expression(source, expression)
        out["ok"] = True
        if req["mode"] == "functional":
            out["output"] = json.dumps(trace.result)
            try:
                out["matches"] = trace.error is None and trace.result == json.loads(req["expected"])
            except Exception:
                out["matches"] = False
            out["report"] = trace.text(expected=req["expected"], config=config)
        else:
            out["output"] = captured.getvalue()
            out["matches"] = trace.error is None and out["output"].split() == req["expected"].split()
            out["report"] = trace.text(expected=req["expected"], output=out["output"], config=config)
        if trace.error is not None:
            out["error"] = f"{type(trace.error).__name__}: {trace.error}"
    except TraceLimit:
        out["error"] = "trace_limit"
    except BaseException as exc:  # noqa
        out["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        sys.stdin = original_stdin
    return out
