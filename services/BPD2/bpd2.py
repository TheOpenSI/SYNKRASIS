"""
Entry point of the compact trace. Same tracer as services.BPD, different report.

    trace = CompactDebugger().run(source, "count_even", [1, 2, 3, 4])
    print(trace.text(expected="2"))

- run(source, entry_point, *args): call a function defined in source
- run_expression(source, expression): evaluate an expression in the namespace of source,
  e.g. "Solution().f([1, 2])" or "__bpd_main__()"
- Trace.text(expected, output, config): the compact report, re-rendered with less detail
  (CompactConfig.tightened) until it fits config.max_chars.
"""
from __future__ import annotations

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from dataclasses import dataclass
from typing import Any, Callable, Optional

from services.BPD.bpd import BreakpointDebugger, TARGET_FILENAME
from services.BPD.parser.structure import CodeStructure
from services.BPD.tracer import Invocation
from services.BPD2.fast_tracer import FastTraceCollector
from services.BPD2.compact_report import CompactConfig, CompactReportBuilder


@dataclass
class Trace:
    structure: CodeStructure
    roots: list[Invocation]
    result: Any
    error: Optional[Exception]

    def text(self, expected: Optional[str] = None, output: Optional[str] = None,
             config: Optional[CompactConfig] = None) -> str:
        config = config or CompactConfig()

        def render(cfg: CompactConfig) -> str:
            return CompactReportBuilder(self.structure, cfg).build_compact(
                self.roots, self.result, self.error, expected, output)

        text = render(config)
        if config.max_chars is None or len(text) <= config.max_chars:
            return text
        for level in (1, 2, 3):
            text = render(config.tightened(level))
            if len(text) <= config.max_chars:
                return text
        lines = text.split("\n")                                   # last resort: cut the middle
        head, tail = int(len(lines) * 0.6), int(len(lines) * 0.25)
        while len("\n".join(lines[:head] + lines[-tail:])) > config.max_chars and head > 10:
            head, tail = int(head * 0.8), int(tail * 0.8)
        omitted = len(lines) - head - tail
        return "\n".join(lines[:head] + [f"... {omitted} lines omitted (size limit) ..."] + lines[-tail:])


class CompactDebugger:

    def __init__(self, max_value_length: int = 1000, max_steps: int = 20000, max_seconds: float = 5.0) -> None:
        self.max_value_length = max_value_length      # values are recorded this long, shown shorter
        self.max_steps = max_steps                    # a longer trace raises fast_tracer.TraceLimit
        self.max_seconds = max_seconds

    def run(self, source: str, entry_point: str, *args: Any, **kwargs: Any) -> Trace:
        namespace = BreakpointDebugger._load(source)
        target = BreakpointDebugger._lookup(namespace, entry_point)
        return self._trace(source, lambda: target(*args, **kwargs))

    def run_expression(self, source: str, expression: str) -> Trace:
        namespace = BreakpointDebugger._load(source)
        code = compile(expression, "<bpd-driver>", "eval")
        return self._trace(source, lambda: eval(code, namespace))

    def _trace(self, source: str, thunk: Callable[[], Any]) -> Trace:
        structure = CodeStructure(source)
        collector = FastTraceCollector(TARGET_FILENAME, structure, self.max_value_length, self.max_steps, self.max_seconds)
        result, error, roots = collector.run(thunk)
        return Trace(structure, roots, result, error)
