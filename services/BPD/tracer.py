"""
Runtime trace of a piece of code, collected with sys.settrace.

For every executed line of every function that lives in the traced source, a Step records the local
variables just before and just after the line ran, the calls the line made into other traced
functions, and any exception it raised. One Invocation per call groups these steps, so recursion and
helper calls form a tree.

Values are stored as (truncated) repr strings rather than live objects, so mutable objects are
captured as they were at that moment.

Safety: a trace is abandoned with TraceLimit after max_steps lines or max_seconds, and a huge list or
dict is stored as its first items plus its length (a repr of 2 million elements on every line made
tracing hang). Two details the first version got wrong: a variable assigned on a line is recorded
every time the line runs (also when the value did not change), and a name is hidden as a
"comprehension variable" only when the function never assigns it as a normal variable.
"""
from __future__ import annotations

import ast
import dis
import inspect
import sys
import time
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from services.BPD.structure import CodeStructure

# Frames Python creates for comprehensions (before 3.12 inlined them). They
# are not functions the user wrote, so they are not traced; calls made from
# inside them are attributed to the enclosing function instead.
TARGET_FILENAME = "<bpd>"      # file name the traced source is compiled with; only frames of this file are recorded

_COMPREHENSION_FRAMES = {"<listcomp>", "<dictcomp>", "<setcomp>", "<genexpr>"}
_GENERATOR_FLAGS = inspect.CO_GENERATOR | inspect.CO_ASYNC_GENERATOR | inspect.CO_COROUTINE
_YIELD_OPCODE = dis.opmap.get("YIELD_VALUE")
_RESUME_OPCODE = dis.opmap.get("RESUME")   # 3.11+: a resumed generator reports f_lasti at the RESUME after the yield


_BIG_CONTAINER = 40    # containers longer than this are summarised
_SHOWN_ITEMS = 8       # items shown from a summarised container


class TraceLimit(BaseException):
    """Raised inside the traced code when the step or time limit is hit (a BaseException: `except Exception` does not catch it)."""


def _summarise(value: Any) -> str:
    """First items and length of a big container: [1, 2, 3, ... (len=2000000)]."""
    if isinstance(value, dict):
        items = [f"{safe_repr(k, 20)}: {safe_repr(v, 20)}" for k, v in list(value.items())[:_SHOWN_ITEMS]]
        opening, closing = "{", "}"
    else:
        iterator = iter(value)
        items = [safe_repr(next(iterator), 20) for _ in range(_SHOWN_ITEMS)]
        opening, closing = {list: ("[", "]"), tuple: ("(", ")")}.get(type(value), ("{", "}"))
    return f"{opening}{', '.join(items)}, ... (len={len(value)}){closing}"


def safe_repr(value: Any, max_length: int = 200, _depth: int = 0) -> str:
    """
    A repr that never raises, keeps to one line, and renders plain objects
    (those without their own __repr__) as ClassName(attr=value, ...).
    A __repr__ replacement for objects that don't have one is provided, so that the report can show
    the values of their attributes. The result is truncated to max_length.
    
    Args:
        value: The thing to represent.
        max_length: The maximum length of the resulting string.
        _depth: The current depth of recursion.
        
    Returns:
        str: A string representation of the value, truncated to max_length.
    """
    try:
        if isinstance(value, (list, tuple, set, frozenset, dict)) and len(value) > _BIG_CONTAINER:
            text = _summarise(value)
        elif isinstance(value, types.ModuleType):
            text = f"<module {value.__name__}>"
        elif isinstance(value, type):
            text = f"<class {value.__name__}>"
        elif isinstance(value, (types.FunctionType, types.BuiltinFunctionType,
                                types.MethodType, types.BuiltinMethodType)):
            text = f"<function {getattr(value, '__qualname__', 'N/A')}>"
        elif type(value).__repr__ is object.__repr__ and hasattr(value, "__dict__"):
            if _depth >= 2:
                text = f"{type(value).__name__}(...)"
            else:
                fields = ", ".join(
                    f"{k}={safe_repr(v, max_length, _depth + 1)}"
                    for k, v in vars(value).items() if not k.startswith("_")
                )
                text = f"{type(value).__name__}({fields})"
        else:
            text = repr(value)
    except Exception:
        text = f"<{type(value).__name__} (unrepresentable, infer to the best of your ability)>"
    text = text.replace("\n", "\\n")
    if len(text) > max_length:
        text = text[:max_length - 3] + "..."
    return text


@dataclass
class ExceptionInfo:
    type_name: str
    message: str
    line: int
    identity: int = 0   # id() of the exception object: the same exception seen in several frames matches

    def __str__(self) -> str:
        return f"{self.type_name}: {self.message}" if self.message else self.type_name


@dataclass
class Step:
    line: int
    before: dict[str, str]
    after: dict[str, str] = field(default_factory=dict)
    calls: list["Invocation"] = field(default_factory=list)
    exception: Optional[ExceptionInfo] = None
    assigned: frozenset = frozenset()    # plain names the statement on this line assigns

    def changes(self) -> dict[str, tuple[Optional[str], str]]:
        """Variables that are new or different after the line ran, plus the ones assigned (even if unchanged): name -> (before, after)."""
        result = {
            name: (self.before.get(name), value)
            for name, value in self.after.items()
            if self.before.get(name) != value
        }
        for name in self.assigned:
            if name in self.after and name not in result:
                result[name] = (self.before.get(name), self.after[name])
        return result


@dataclass
class Invocation:
    name: str
    first_line: int
    depth: int
    args: dict[str, str]
    is_generator: bool = False
    steps: list[Step] = field(default_factory=list)
    children: list["Invocation"] = field(default_factory=list)
    finished: bool = False
    return_value: Optional[str] = None
    return_line: Optional[int] = None
    final_state: dict[str, str] = field(default_factory=dict)
    raised: Optional[ExceptionInfo] = None
    yields: list[str] = field(default_factory=list)
    # bookkeeping used while collecting; not meaningful afterwards
    _current_step: Optional[Step] = field(default=None, repr=False)
    _last_exception: Optional[ExceptionInfo] = field(default=None, repr=False)
    _last_returned_child: Optional["Invocation"] = field(default=None, repr=False)

    @property
    def returned_normally(self) -> bool:
        return self.finished and self.raised is None

    def signature(self) -> str:
        return f"{self.name}({', '.join(f'{k}={v}' for k, v in self.args.items())})"


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


class TraceCollector:
    """
    Traces one call and returns the tree of Invocations it produced.

    Only frames whose code was compiled from `filename` are recorded, so
    library code the block calls into is invisible, while calls between the
    block's own functions (including recursion) are captured in full.
    """

    def __init__(self, filename: str, structure: Optional[CodeStructure] = None, max_value_length: int = 1000,
                 max_steps: int = 20000, max_seconds: float = 5.0) -> None:
        self.filename = filename
        self.structure = structure
        self.max_value_length = max_value_length
        self.max_steps = max_steps
        self.max_seconds = max_seconds
        self.steps = 0
        self._started = time.monotonic()
        tree = ast.parse(structure.source) if structure is not None else None
        self._assigned = _assigned_names_by_line(tree) if tree is not None else {}
        self._real_names = _real_variable_names(tree) if tree is not None else {}
        self.roots: list[Invocation] = []
        self._open: dict[int, Invocation] = {}   # id(frame) -> invocation still running

    def run(self, thunk: Callable[[], Any]) -> tuple[Any, Optional[Exception], list[Invocation]]:
        """Runs thunk() under tracing. Returns (result, exception or None, root invocations)."""
        self.roots = []
        self._open = {}
        self.steps = 0
        self._started = time.monotonic()
        result = None
        error: Optional[Exception] = None
        sys.settrace(self._trace)
        try:
            result = thunk()
        except Exception as exc:
            error = exc
        finally:
            sys.settrace(None)
        if error is not None:
            for root in self.roots:
                last = root._last_exception
                if last is not None and last.identity == id(error):
                    root.raised = last
        return result, error, self.roots

    # -- trace callbacks ------------------------------------------------------

    def _trace(self, frame: types.FrameType, event: str, arg: Any):
        code = frame.f_code
        if code.co_filename != self.filename or code.co_name in _COMPREHENSION_FRAMES:
            return None
        if event == "call":
            self._on_call(frame)
        elif event == "line":
            self._on_line(frame)
        elif event == "exception":
            self._on_exception(frame, arg)
        elif event == "return":
            self._on_return(frame, arg)
        return self._trace

    def _on_call(self, frame: types.FrameType) -> None:
        code = frame.f_code
        existing = self._open.get(id(frame))
        if existing is not None and existing.is_generator and frame.f_lineno != code.co_firstlineno:
            # a generator resuming after a yield: same invocation, new step
            existing._current_step = None
            return
        parent = self._parent_of(frame)
        node = Invocation(
            name=code.co_name,
            first_line=code.co_firstlineno,
            depth=parent.depth + 1 if parent else 0,
            args=self._snapshot(frame),
            is_generator=bool(code.co_flags & _GENERATOR_FLAGS),
        )
        if parent is not None:
            parent.children.append(node)
            if parent._current_step is not None:
                parent._current_step.calls.append(node)
        else:
            self.roots.append(node)
        self._open[id(frame)] = node

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
        step = Step(line=frame.f_lineno, before=snapshot, assigned=self._assigned.get(frame.f_lineno, frozenset()))
        node.steps.append(step)
        node._current_step = step

    def _on_exception(self, frame: types.FrameType, arg: Any) -> None:
        node = self._open.get(id(frame))
        if node is None:
            return
        exc_type, exc_value, _ = arg
        try:
            message = str(exc_value)
        except Exception:
            message = ""
        info = ExceptionInfo(
            type_name=exc_type.__name__,
            message=message[: self.max_value_length],
            line=frame.f_lineno,
            identity=id(exc_value),
        )
        if node._current_step is None:
            step = Step(line=frame.f_lineno, before=self._snapshot(frame))
            node.steps.append(step)
            node._current_step = step
        node._current_step.exception = info
        node._last_exception = info
        # the child that just returned raised this very exception into us
        child = node._last_returned_child
        if child is not None and child._last_exception is not None \
                and child._last_exception.identity == info.identity:
            child.raised = child._last_exception

    def _on_return(self, frame: types.FrameType, arg: Any) -> None:
        node = self._open.get(id(frame))
        if node is None:
            return
        snapshot = self._snapshot(frame)
        if node._current_step is not None:
            node._current_step.after = snapshot
        if node.is_generator and self._is_yield(frame):
            node.yields.append(safe_repr(arg, self.max_value_length))
            node._current_step = None
            return
        node.finished = True
        node.final_state = snapshot
        node.return_line = frame.f_lineno
        node.return_value = safe_repr(arg, self.max_value_length)
        del self._open[id(frame)]
        parent = self._parent_of(frame)
        if parent is not None:
            parent._last_returned_child = node

    # -- helpers --------------------------------------------------------------

    def _parent_of(self, frame: types.FrameType) -> Optional[Invocation]:
        """Nearest calling frame that belongs to the traced source (library frames are skipped)."""
        caller = frame.f_back
        while caller is not None:
            node = self._open.get(id(caller))
            if node is not None:
                return node
            caller = caller.f_back
        return None

    def _snapshot(self, frame: types.FrameType) -> dict[str, str]:
        code = frame.f_code
        info = None
        if self.structure is not None:
            info = self.structure.function_for(code.co_name, code.co_firstlineno)
        real = self._real_names.get((code.co_name, code.co_firstlineno), set())
        hidden = info.comprehension_names - real if info is not None else set()
        snapshot: dict[str, str] = {}
        for name, value in list(frame.f_locals.items()):
            if name.startswith("__") or name in hidden or isinstance(value, types.ModuleType):
                continue
            snapshot[name] = safe_repr(value, self.max_value_length)
        if info is not None:
            for name in sorted(info.global_names):
                if name in frame.f_globals:
                    snapshot[f"{name} (global)"] = safe_repr(frame.f_globals[name], self.max_value_length)
        return snapshot

    @staticmethod
    def _is_yield(frame: types.FrameType) -> bool:
        """True when a generator frame's 'return' event is really a yield."""
        try:
            code = frame.f_code.co_code
            offset = frame.f_lasti
            if code[offset] == _YIELD_OPCODE:
                return True
            return code[offset] == _RESUME_OPCODE and offset >= 2 and code[offset - 2] == _YIELD_OPCODE
        except (IndexError, TypeError):
            return False
