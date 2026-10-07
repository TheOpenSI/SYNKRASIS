"""
TraceCollector with four changes (services/BPD/tracer.py is untouched):
  - bounded_repr: a huge list/dict/set is shown as its first items plus its length, instead of
    building a repr of every element on every traced line (a 2 million element list made each step take 100ms).
  - limits: the trace is abandoned with TraceLimit after max_steps lines or max_seconds of tracing.
  - assigned variables are recorded on every execution of the line, also when the value did not change
    (`t = T[j]` run 6 times gives 6 values, the old tracer only reported the ones that differed from the previous).
  - a name is hidden as "comprehension variable" only when the function never assigns it as a normal variable
    (the old tracer hid `col` everywhere in a function that also had `... for col in cols`).
"""
from __future__ import annotations

import ast
import time
import types
from dataclasses import dataclass
from typing import Any, Optional

from services.BPD.parser.structure import CodeStructure
from services.BPD.tracer import Step, TraceCollector, safe_repr

BIG = 40          # containers longer than this are summarised
SHOWN = 8         # items shown from a summarised container


class TraceLimit(BaseException):
    """Raised inside the traced code when the step or time limit is hit (BaseException: not caught by `except Exception`)."""


def bounded_repr(value: Any, max_length: int) -> str:
    try:
        if isinstance(value, (list, tuple, set, frozenset, dict)) and len(value) > BIG:
            if isinstance(value, dict):
                items = [f"{safe_repr(k, 20)}: {safe_repr(v, 20)}" for k, v in list(value.items())[:SHOWN]]
                opening, closing = "{", "}"
            else:
                iterator = iter(value)
                items = [safe_repr(next(iterator), 20) for _ in range(SHOWN)]
                opening, closing = {list: ("[", "]"), tuple: ("(", ")")}.get(type(value), ("{", "}"))
            return f"{opening}{', '.join(items)}, ... (len={len(value)}){closing}"
    except Exception:
        pass
    return safe_repr(value, max_length)


@dataclass
class FullStep(Step):
    assigned: frozenset = frozenset()      # names assigned by the statement on this line

    def changes(self) -> dict[str, tuple[Optional[str], str]]:
        result = super().changes()
        for name in self.assigned:
            if name in self.after and name not in result:
                result[name] = (self.before.get(name), self.after[name])    # assigned, value unchanged
        return result


def _assigned_names_by_line(tree: ast.AST) -> dict[int, frozenset]:
    """line of an assignment statement -> plain names it assigns (`a, b = ...` gives a and b, `X[i] = ...` none)."""
    assigned: dict[int, set] = {}
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for target in targets:
            for sub in ast.walk(target):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    assigned.setdefault(node.lineno, set()).add(sub.id)
    return {line: frozenset(names) for line, names in assigned.items()}


def _real_variable_names(tree: ast.AST) -> dict[tuple[str, int], set]:
    """(function name, first line) -> names the function assigns outside of comprehensions."""
    result: dict[tuple[str, int], set] = {}
    comprehensions = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

    def stores(node: ast.AST, found: set) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, comprehensions):
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                found.add(child.id)
            stores(child, found)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            first_line = node.decorator_list[0].lineno if node.decorator_list else node.lineno
            found: set = set()
            stores(node, found)
            result[(node.name, first_line)] = found
    return result


class FastTraceCollector(TraceCollector):

    def __init__(self, filename: str, structure: Optional[CodeStructure] = None, max_value_length: int = 100,
                 max_steps: int = 20000, max_seconds: float = 5.0) -> None:
        super().__init__(filename, structure, max_value_length)
        self.max_steps = max_steps
        self.max_seconds = max_seconds
        self.steps = 0
        self._started = time.monotonic()
        tree = ast.parse(structure.source) if structure is not None else None
        self._assigned = _assigned_names_by_line(tree) if tree is not None else {}
        self._real_names = _real_variable_names(tree) if tree is not None else {}

    def run(self, thunk):
        self._started = time.monotonic()
        self.steps = 0
        return super().run(thunk)

    def _on_line(self, frame: types.FrameType) -> None:
        self.steps += 1
        if self.steps > self.max_steps or time.monotonic() - self._started > self.max_seconds:
            raise TraceLimit(f"trace limit: {self.steps} steps")
        node = self._open.get(id(frame))
        if node is None:
            return
        snapshot = self._snapshot(frame)
        if node._current_step is not None:
            node._current_step.after = snapshot
        step = FullStep(line=frame.f_lineno, before=snapshot, assigned=self._assigned.get(frame.f_lineno, frozenset()))
        node.steps.append(step)
        node._current_step = step

    def _snapshot(self, frame: types.FrameType) -> dict[str, str]:
        code = frame.f_code
        info = self.structure.function_for(code.co_name, code.co_firstlineno) if self.structure is not None else None
        hidden = (info.comprehension_names - self._real_names.get((code.co_name, code.co_firstlineno), set())
                  if info is not None else set())
        snapshot: dict[str, str] = {}
        for name, value in list(frame.f_locals.items()):
            if name.startswith("__") or name in hidden or isinstance(value, types.ModuleType):
                continue
            snapshot[name] = bounded_repr(value, self.max_value_length)
        if info is not None:
            for name in sorted(info.global_names):
                if name in frame.f_globals:
                    snapshot[f"{name} (global)"] = bounded_repr(frame.f_globals[name], self.max_value_length)
        return snapshot
