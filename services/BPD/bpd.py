"""
BPD: Breakpoint Debugger.

Runs a block of Python code with given inputs and produces a text report of
what happened inside: variable values line by line, loop iterations, branch
decisions, calls, returns and exceptions. The report is meant to be handed
to an LLM as a substitute for setting breakpoints and stepping through.

    from services.BPD.bpd import BreakpointDebugger

    report = BreakpointDebugger().run(source_code, "sum_list", [1, 2, 3])
    print(report.text)

The code is executed in this process, so only run code you would run anyway.
"""
from __future__ import annotations

import inspect
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from services.BPD.parser.structure import CodeStructure
from services.BPD.report import ReportBuilder, ReportConfig
from services.BPD.tracer import Invocation, TraceCollector, safe_repr

TARGET_FILENAME = "<bpd>"


@dataclass
class DebugReport:
    text: str                       # the narrative for the LLM
    call_description: str
    result: Any = None              # what the call returned, if it returned
    exception: Optional[Exception] = None
    invocations: list[Invocation] = field(default_factory=list)   # structured trace, if you need it

    def __str__(self) -> str:
        return self.text


class BreakpointDebugger:

    def __init__(self, config: Optional[ReportConfig] = None) -> None:
        self.config = config or ReportConfig()


    def run(self, 
            source: str, 
            entry_point: str, 
            *args: Any, 
            **kwargs: Any) -> DebugReport:
        """
        Executes `entry_point(*args, **kwargs)` where entry_point is the name of a function defined in `source`.
        """
        namespace = self._load(source)
        target = self._lookup(namespace, entry_point)
        rendered = [safe_repr(a, self.config.max_value_length) for a in args]
        rendered += [f"{k}={safe_repr(v, self.config.max_value_length)}" for k, v in kwargs.items()]
        description = f"{entry_point}({', '.join(rendered)})"
        return self._execute(CodeStructure(source), TARGET_FILENAME, description,
                             lambda: target(*args, **kwargs))


    def run_expression(self, source: str, expression: str) -> DebugReport:
        """
        Evaluates a Python expression in the namespace of `source`, e.g.
        "Counter(5).increment(3)" or "sum_list([1, 2, 3])". Useful for
        methods, and for test cases written as expressions.
        """
        namespace = self._load(source)
        code = compile(expression, "<bpd-driver>", "eval")
        return self._execute(CodeStructure(source), TARGET_FILENAME, expression,
                             lambda: eval(code, namespace))


    def run_callable(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> DebugReport:
        """
        Traces an already-imported function. Every function defined in the
        same file is traced too, so helpers it calls show up in the report.
        """
        code = inspect.unwrap(func).__code__ if not inspect.ismethod(func) else func.__func__.__code__
        filename = code.co_filename
        with open(filename, encoding="utf-8") as handle:
            source = handle.read()
        rendered = [safe_repr(a, self.config.max_value_length) for a in args]
        rendered += [f"{k}={safe_repr(v, self.config.max_value_length)}" for k, v in kwargs.items()]
        description = f"{getattr(func, '__qualname__', code.co_name)}({', '.join(rendered)})"
        return self._execute(CodeStructure(source, from_file=True), filename, description,
                             lambda: func(*args, **kwargs))


    @staticmethod
    def _load(source: str) -> dict[str, Any]:
        """
        Loads the source code into a namespace and returns it. Raises SyntaxError if the source is invalid.
        
        Args:
            source: The source code to load.
            
        Returns:
            A dictionary representing the namespace containing the loaded source code.
        """
        
        namespace: dict[str, Any] = {"__name__": "__bpd_target__"}
        exec(compile(source, TARGET_FILENAME, "exec"), namespace) # to get natural error message, like error in <bpd>:3
        return namespace


    @staticmethod
    def _lookup(namespace: dict[str, Any], dotted: str) -> Any:
        """
        Looks up a dotted name in the given namespace, e.g. Class defined in the source, or a function defined in a class.
        Raises NameError if not found. Also supports dotted names like "Class.method" or "module.submodule.Class.method"
        
        Args:
            namespace: The namespace to look up the name in.
            dotted: The dotted name to look up.
            
        Returns:
            The object corresponding to the dotted name.
        """
        first, *rest = dotted.split(".")
        if first not in namespace:
            raise NameError(f"Entrypoint '{first}' is not defined in the given source")
        target = namespace[first]
        for part in rest:
            target = getattr(target, part)
        return target


    def _execute(self, structure: CodeStructure, filename: str, description: str,
                 thunk: Callable[[], Any]) -> DebugReport:
        collector = TraceCollector(filename, structure, self.config.max_value_length)
        result, error, roots = collector.run(thunk)
        text = ReportBuilder(structure, self.config).build(description, roots, result, error)
        return DebugReport(text=text, call_description=description, result=result,
                           exception=error, invocations=roots)
        
        
if __name__ == "__main__":
    source_code = """
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    debugger = BreakpointDebugger()
    report = debugger.run(source_code, "factorial", 5)
    print(report.text)
