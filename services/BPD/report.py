from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field, replace
from typing import Any, Optional

from services.BPD.analysis import Analyser
from services.BPD.structure import CodeStructure
from services.BPD.tracer import Invocation

SEPARATOR = "  # "
HARD_LIMIT_FACTOR = 1.5       # a trace is never longer than max_chars * this (the shrinking before it can leave a long program over max_chars)


@dataclass
class TraceConfig:
    sequence_plain: int = 6        # sequences up to this long are written out completely
    sequence_head: int = 4         # longer ones keep this many values at the start ...
    sequence_tail: int = 2         # ... and this many at the end
    value_length: int = 40         # longer values are clipped
    max_note: Optional[int] = None  # longer notes after a line are clipped (the code itself never is)
    max_chars: Optional[int] = 6000

    def tightened(self, level: int) -> "TraceConfig":
        """Less detail, level 1, 2, 3, used when the trace is over max_chars."""
        plain, head, tail, length = [(5, 3, 2, 30), (4, 2, 1, 24), (3, 2, 1, 16)][min(level, 3) - 1]
        return replace(self, sequence_plain=plain, sequence_head=head, sequence_tail=tail, value_length=length)


@dataclass
class Row:
    """One source line, with every time it executed."""
    line: int
    kind: str                                    # "stmt", "branch", "return", "loop"; "def" (function header), "unreached", "uncalled"
    executions: list[dict]                       # the analysed items (see Analyser._analyse), one per time
    iteration_ids: list[Optional[int]]           # enclosing loop iteration of each execution (None: not in a loop)
    children: list["Row"]                        # loops: the rows of the loop body
    loop_runs: list[dict]                        # loops: the loop items (a nested loop runs once per outer iteration)
    iterations_total: int = 0                    # loops: iterations over all runs
    total_iterations: Optional[int] = None       # iterations of the loop this row is in (None: not in a loop)
    invocations: list[Invocation] = field(default_factory=list)   # "def": the calls of the function


class Renderer(Analyser):

    def __init__(self, structure: CodeStructure, config: Optional[TraceConfig] = None) -> None:
        self.compact = config or TraceConfig()
        super().__init__(structure)


    def render(self, roots: list[Invocation], result: Any, error: Optional[Exception],
                      expected: Optional[str] = None, output: Optional[str] = None) -> str:
        """
        The source with the trace next to it, then one final line with the outcome. expected: the expected
        answer (public tests only). output: what a stdin program printed, when given it replaces the returned value.
        """
        self._items_cache = {}
        lines = self._render_source(roots)
        if not roots:
            lines.append("(no traced function was called)")

        if error is not None:
            outcome = f"raised {type(error).__name__}"
            state = ", ".join(f"{self._display_name(k)}={self._clip(v)}"
                              for k, v in roots[-1].final_state.items() if not self._is_noise(v)) if roots else ""
            if state:
                outcome += f"; locals: {state}"
        elif output is not None:
            outcome = f"printed {self._short(output.strip())!r}"
        else:
            outcome = f"returned {self._short(repr(result))}"
        if expected is not None:
            outcome += f"   (expected {self._short(repr(expected.strip()))})"
        lines.append(outcome)
        return "\n".join(lines)

    def _render_source(self, roots: list[Invocation]) -> list[str]:
        """Every line of the source in order, with the values of the line (if it has a row) after `#`."""
        calls: dict[tuple[str, int], list[Invocation]] = {}      # function -> its calls, in the order they happened
        pending = list(reversed(roots))
        while pending:
            inv = pending.pop()
            calls.setdefault((inv.name, inv.first_line), []).append(inv)
            pending.extend(reversed(inv.children))
        rows: dict[int, Row] = {}
        for info in self.structure.functions:
            if (info.name, info.first_line) in calls:
                rows.update(self._function_rows(info, calls[(info.name, info.first_line)]))
            else:
                rows[info.def_line] = Row(info.def_line, "uncalled", [], [], [], [])

        main = next((f for f in self.structure.functions if f.name == "__bpd_main__"), None)   # wrapper of a stdin program
        lines: list[str] = []
        for number, text in enumerate(self.structure.lines, start=1):
            if not text.strip() or (main is not None and (number == main.def_line or (number == main.def_line + 1 and text.strip().startswith("global ")))):
                continue
            indent = len(text) - len(text.lstrip())
            if main is not None and main.def_line < number <= main.end_line:
                indent -= 4                                           # the body of the wrapper is the program itself
            line = " " * indent + text.strip()
            lines.append(line + (self._note(rows[number]) if number in rows else ""))
        return lines

    def _function_rows(self, info, invocations: list[Invocation]) -> dict[int, Row]:
        """One row per statement line of a function, over all its calls; a line that never ran gets an "unreached" row."""
        rows: dict[int, Row] = {}

        def add(built: list[Row]) -> None:
            for row in built:
                rows[row.line] = row
                add(row.children)

        add(self._build_rows([(None, self._items_for(inv)) for inv in invocations]))
        for line in info.statement_lines:
            rows.setdefault(line, Row(line, "unreached", [], [], [], []))
        rows[info.def_line] = Row(info.def_line, "def", [], [], [], [], invocations=invocations)
        return rows

    def _note(self, row: Row) -> str:
        """What goes after the source text of the line: `  # values; values  (iterations 2,4)`."""
        if row.kind == "loop":
            parts = self._loop_parts(row)
        elif row.kind == "def":
            parts = [self._arguments_part(row.invocations)]
        elif row.kind == "unreached":
            parts = ["never reached"]
        elif row.kind == "uncalled":
            parts = ["never called"]
        else:
            parts = self._statement_parts(row)
        text = SEPARATOR + "; ".join(parts) if parts else ""
        sparse = self._sparse_note(row, row.total_iterations)
        text += "  " + sparse if sparse else ""                  # a note about the row, apart from its values
        limit = self.compact.max_note
        return text if limit is None or len(text) <= limit else text[:limit - 3] + "..."

    def _arguments_part(self, invocations: list[Invocation]) -> str:
        """The arguments of all calls of a function: `x=3,2,1`."""
        parts = []
        for name in dict.fromkeys(name for inv in invocations for name in inv.args):
            values = [inv.args[name] for inv in invocations if name in inv.args]
            if name != "self" and not self._is_noise(values[0]):
                parts.append(f"{self._display_name(name)}={self._sequence([self._clip(v) for v in values])}")
        count = len(invocations)
        return ", ".join(parts) or "called" + (f" {count} times" if count > 1 else "")


    def _build_rows(self, groups: list[tuple[Optional[int], list[dict]]], total_iterations: Optional[int] = None) -> list[Row]:
        """
        groups: (iteration id, items executed in it). Returns one Row per source line that ran, in source order;
        a loop row has the rows of its body as children.
        """
        by_line: dict[int, Row] = {}
        for iteration_id, items in groups:
            for item in items:
                if item.get("implicit"):
                    continue                                        # "end of function reached", not a line
                row = by_line.setdefault(item["line"], Row(item["line"], item["kind"], [], [], [], [],
                                                           total_iterations=total_iterations))
                if item["kind"] == "loop":
                    row.loop_runs.append(item)
                row.executions.append(item)
                row.iteration_ids.append(iteration_id)
        for row in by_line.values():
            if row.kind == "loop":
                pooled = [(number, iteration["items"])
                          for number, iteration in enumerate(self._all_iterations(row), start=1)]
                row.iterations_total = len(pooled)
                row.children = self._build_rows(pooled, len(pooled))
        return [by_line[line] for line in sorted(by_line)]

    @staticmethod
    def _all_iterations(row: Row) -> list[dict]:
        return [iteration for run in row.loop_runs for iteration in run["iterations"]]


    def _loop_parts(self, row: Row) -> list[str]:
        iterations = self._all_iterations(row)
        counts = [run["count"] for run in row.loop_runs]
        total = sum(counts)
        if len(row.loop_runs) == 1:
            text = f"{total} iteration{'s' if total != 1 else ''}"
        else:
            text = f"{len(row.loop_runs)} runs, iterations per run: {self._sequence([str(c) for c in counts])}"
        parts = [text]

        names = list(dict.fromkeys(name for iteration in iterations for name in iteration["values"]))
        for name in names:
            values = [iteration["values"][name] for iteration in iterations if name in iteration["values"]]
            if self._is_noise(values[0]) or (len(values) > 1 and len(set(values)) == 1):
                continue                                             # does not change: it is in the code / above
            parts.append(f"{self._display_name(name)}={self._sequence([self._clip(v) for v in values])}")

        exits = {run["exit"] for run in row.loop_runs} - {"completed"}
        if exits:
            parts.append("ended by " + "/".join(sorted(exits)))
        return parts


    def _statement_parts(self, row: Row) -> list[str]:
        executions = row.executions
        parts: list[str] = []

        if row.kind == "branch" or any(e["kind"] == "branch" for e in executions):
            parts.append(self._branch_part(executions))

        changes = {}
        written: dict[str, list[tuple[str, str]]] = {}
        if not self._is_literal_assignment(self.structure.line_source(row.line)):
            for execution in executions:
                for name, (before, after) in execution.get("changes", {}).items():
                    if not self._is_noise(after):
                        changes.setdefault(name, []).append((before, after))
                for target, slot_and_value in execution.get("written", {}).items():
                    written.setdefault(target, []).append(slot_and_value)
        else:
            parts.append("literal assignment")
        # `G[i][j] = x` is shown by the values it wrote, not by how the whole list G changed
        changes = {name: pairs for name, pairs in changes.items()
                   if name not in {re.match(r"\w+", target).group() for target in written}}
        has_calls = any(not c.name.startswith("<") for e in executions for c in e.get("calls", []))
        if has_calls or written:    # a callee changed a list/dict (its own lines show how), or the line wrote into one (shown by `written`)
            changes = {n: p for n, p in changes.items() if not all(self._is_container_change(b, a) for b, a in p)}
        change_texts = [self._variable_part(name, pairs) for name, pairs in changes.items()]
        parts.extend(text for text in change_texts if text)
        parts.extend(self._written_part(target, pairs) for target, pairs in written.items())

        returned = [e["value"] for e in executions if e.get("value") is not None and (e["kind"] == "return" or e.get("returns"))]
        if returned:
            parts.append("returns " + self._sequence([self._clip(v) for v in returned]))

        call_part = self._calls_text(row, changes)
        if call_part:
            parts.append(call_part)

        for execution, iteration in zip(executions, row.iteration_ids):
            exception = execution.get("exception")
            if exception is not None and not self._raised_inside_call(execution):
                parts.append(f"raised {exception}" + (f" (iteration {iteration})" if iteration is not None else ""))
                break
        return parts

    def _branch_part(self, executions: list[dict]) -> str:
        """
        Outcomes as T/F. Values of the condition are added for a single execution, and for repeated branches only
        short values that never change (the ones that change are the loop variables or the rows above).
        """
        branches = [e for e in executions if e["kind"] == "branch"]
        outcomes = ["T" if e.get("outcome") else "F" if e.get("outcome") is False else "?" for e in branches]
        names = list(dict.fromkeys(name for e in branches for name in e.get("values", {})))
        shown = []
        for name in names:
            values = [e["values"][name] for e in branches if name in e.get("values", {})]
            if self._is_noise(values[0]):
                continue
            if len(branches) == 1 or (len(set(values)) == 1 and len(values[0]) <= 24):
                shown.append(f"{self._display_name(name)}={self._clip(values[0])}")
        suffix = f" ({', '.join(shown)})" if shown else ""
        if len(outcomes) == 1:
            return {"T": "True", "F": "False", "?": "evaluated"}[outcomes[0]] + suffix
        return self._outcome_sequence(outcomes) + suffix

    def _outcome_sequence(self, outcomes: list[str]) -> str:
        """T/F per execution. Few changes of outcome: the whole run-length form (F,T,F×118). Otherwise head, tail and counts."""
        runs = 1 + sum(1 for a, b in zip(outcomes, outcomes[1:]) if a != b)
        if runs <= 8 or len(outcomes) <= self.compact.sequence_plain + 6:
            return self._run_length(outcomes)
        head, tail = outcomes[:self.compact.sequence_head + 2], outcomes[-self.compact.sequence_tail - 1:]
        counts = ", ".join(f"{symbol} {outcomes.count(symbol)}" for symbol in ("T", "F", "?") if symbol in outcomes)
        return f"{self._run_length(head)} ... {self._run_length(tail)} ({len(outcomes)} times: {counts})"

    def _variable_part(self, name: str, pairs: list[tuple[Optional[str], str]]) -> str:
        display = self._display_name(name)
        if len(pairs) == 1:
            before, after = pairs[0]
            event = self._container_event(before, after)
            if event is not None:
                return self._compress_events(display, [event])
            delta = self._delta(display, before, after)
            return delta if delta is not None else f"{display}={self._clip(after)}"
        events = [self._container_event(before, after) for before, after in pairs]
        if all(event is not None for event in events):
            compact = self._compress_events(display, events)
            if compact:
                return compact
        return f"{display}={self._sequence([self._clip(after) for _, after in pairs])}"

    @staticmethod
    def _is_container_change(before: Optional[str], after: str) -> bool:
        return before is not None and after[:1] in "[{(" and before[:1] in "[{(" or after.startswith("deque(")

    def _container_event(self, before: Optional[str], after: str) -> Optional[tuple]:
        """
        A list update as an event: ("set", index, value) one slot replaced, ("slot_add", index, item) an item
        appended to a list inside a slot, ("add", [items]) items appended at the end. None for anything else.
        """
        if before is None:
            return None
        try:
            old, new = ast.literal_eval(self._strip_deque(before)), ast.literal_eval(self._strip_deque(after))
        except Exception:
            return None
        if not (isinstance(old, list) and isinstance(new, list)):
            return None
        if len(new) < len(old):                     # items taken from the end (pop) or the start (popleft)
            removed = len(old) - len(new)
            if old[:len(new)] == new:
                return ("pop", [repr(x) for x in old[len(new):]])
            if old[removed:] == new:
                return ("popleft", [repr(x) for x in old[:removed]])
            return None
        if len(old) == len(new):
            changed = [i for i in range(len(new)) if old[i] != new[i]]
            if len(changed) != 1:
                return None
            i = changed[0]
            if isinstance(old[i], list) and isinstance(new[i], list) and len(new[i]) == len(old[i]) + 1 and new[i][:-1] == old[i]:
                return ("slot_add", i, repr(new[i][-1]))
            return ("set", i, repr(new[i]))
        if len(new) > len(old) and new[:len(old)] == old:
            return ("add", [repr(x) for x in new[len(old):]])
        return None

    def _compress_events(self, name: str, events: list[tuple]) -> Optional[str]:
        if all(event[0] == "set" for event in events):
            indices = [event[1] for event in events]
            values = self._sequence([self._clip(event[2]) for event in events])
            if len(indices) == 1:
                return f"{name}[{indices[0]}]={values}"
            if all(b - a == 1 for a, b in zip(indices, indices[1:])):
                return f"{name}[{indices[0]}..{indices[-1]}]={values}"
            return f"{name}[{self._sequence([str(i) for i in indices])}]={values}"
        if all(event[0] == "add" for event in events):
            added = [self._clip(value) for event in events for value in event[1]]
            return f"{name} += {self._sequence(added)}"
        pieces = [f"[{e[1]}]={self._clip(e[2])}" if e[0] == "set" else
                  f"[{e[1]}]+={self._clip(e[2])}" if e[0] == "slot_add" else
                  f"{e[0]} {self._clip(', '.join(e[1]))}" if e[0] in ("pop", "popleft") else
                  f"+={self._clip(', '.join(e[1]))}" for e in events]
        return f"{name}: {self._sequence(pieces)}"

    @staticmethod
    def _strip_deque(text: str) -> str:
        return text[6:-1] if text.startswith("deque(") and text.endswith(")") else text

    def _written_part(self, target: str, pairs: list[tuple[str, str]]) -> str:
        """
        What `G[i][j] = ...` wrote, with the slots: pairs are (slot, value) per execution.
          one dimension, consecutive slots   X[0..4]=1,1,2,3,2
          anything else                      A[0][0]=1,A[0][1]=2,...   (head and tail when long)
        An attribute (self.count) has no index: self.count=2,4,6
        """
        slots = [slot for slot, _ in pairs]
        values = [self._clip(value) for _, value in pairs]
        if all(slot == target for slot in slots):
            return f"{target}={self._sequence(values)}"
        matches = [re.fullmatch(r"(.*)\[(-?\d+)\]", slot) for slot in slots]
        if all(matches) and len({m.group(1) for m in matches}) == 1:
            indices = [int(m.group(2)) for m in matches]
            if len(indices) == 1 or all(b - a == 1 for a, b in zip(indices, indices[1:])):
                where = f"[{indices[0]}]" if len(indices) == 1 else f"[{indices[0]}..{indices[-1]}]"
                return f"{matches[0].group(1)}{where}={self._sequence(values)}"
        return self._sequence([f"{slot}={value}" for slot, value in zip(slots, values)])

    def _calls_text(self, row: Row, changes: dict) -> str:
        """The values the traced functions called on this line returned: `f returns 4,1,3`. The body of f is listed at its def."""
        calls = [c for e in row.executions for c in e.get("calls", []) if not c.name.startswith("<")]
        pieces = []
        for name in dict.fromkeys(c.name for c in calls):
            returns = [self._clip(c.return_value if c.raised is None else f"raised {c.raised}") for c in calls if c.name == name]
            if all(r == "None" for r in returns):
                continue                                           # nothing returned: nothing to say
            if row.kind == "branch" and all(r in ("True", "False") for r in returns):
                continue                                           # the branch outcome already says it
            if any(returns == [self._clip(after) for _, after in pairs] for pairs in changes.values()):
                continue                                           # `x = f(y)`: x=... says it
            pieces.append(f"{name} returns {self._sequence(returns)}")
        return "; ".join(pieces)

    @staticmethod
    def _raised_inside_call(execution: dict) -> bool:
        exception = execution.get("exception")
        return exception is not None and any(c.raised is not None and c.raised.identity == exception.identity
                                             for c in execution.get("calls", []))


    def _sparse_note(self, row: Row, total_iterations: Optional[int]) -> str:
        """
        Says in which iterations of the enclosing loop the line ran, only when it ran in fewer than half of them:
        `(iteration 3)`, `(iterations 2,4)`, `(30 of 120 iterations)`. A line that ran in most iterations says
        nothing: the `continue` that skips the rest of an iteration says which ones, `(ends iteration 2)`.
        """
        if total_iterations is None:
            return ""
        ran = sorted({i for i in row.iteration_ids if i is not None})
        is_continue = self.structure.line_source(row.line) == "continue"
        if not ran or (len(ran) * 2 >= total_iterations and not is_continue):
            return ""
        if len(ran) <= 4:
            what = f"{'iteration' if len(ran) == 1 else 'iterations'} {','.join(map(str, ran))}"
        else:
            what = f"{len(ran)} of {total_iterations} iterations"
        return f"({'ends ' if is_continue else ''}{what})"

    @staticmethod
    def _is_noise(value: str) -> bool:
        """Functions, classes, modules and `<X object at 0x..>` say nothing to the reader."""
        return value.startswith(("<function", "<class", "<module", "<built-in", "<bound method")) or " object at 0x" in value

    def _delta(self, name: str, before: Optional[str], after: str) -> Optional[str]:
        """Update of a list/dict/set as a small delta instead of both full values, None if not applicable."""
        if before is None:
            return None
        try:
            old, new = ast.literal_eval(before), ast.literal_eval(after)
        except Exception:
            return None
        show = lambda value: self._clip(repr(value))
        parts: list[str] = []
        if isinstance(old, list) and isinstance(new, list):
            if len(old) == len(new):
                parts = [f"{name}[{i}]: {show(o)} -> {show(n)}" for i, (o, n) in enumerate(zip(old, new)) if o != n]
            elif len(new) > len(old) and new[:len(old)] == old:
                parts = [f"{name}: appended {', '.join(show(x) for x in new[len(old):])}"]
            elif len(new) < len(old) and old[:len(new)] == new:
                parts = [f"{name}: removed {', '.join(show(x) for x in old[len(new):])} from the end"]
        elif isinstance(old, dict) and isinstance(new, dict):
            for key in new:
                if key not in old:
                    parts.append(f"{name}[{key!r}] = {show(new[key])}")
                elif old[key] != new[key]:
                    parts.append(f"{name}[{key!r}]: {show(old[key])} -> {show(new[key])}")
            parts += [f"{name}: removed key {key!r}" for key in old if key not in new]
        elif isinstance(old, set) and isinstance(new, set):
            if new - old:
                parts.append(f"{name}: added {', '.join(show(x) for x in sorted(new - old, key=repr))}")
            if old - new:
                parts.append(f"{name}: removed {', '.join(show(x) for x in sorted(old - new, key=repr))}")
        if not parts or len(parts) > 3:
            return None
        return "; ".join(parts)

    @staticmethod
    def _is_literal_assignment(source: str) -> bool:
        """
        total = 0, seen = []: the value is in the code, a trace row would say nothing.
        
        Args:
            source: A string representing a line of source code.
        
        Returns:
            True if the source line is an assignment of a literal value, False otherwise.
        """
        try:
            node = ast.parse(source.strip()).body[0]
        except Exception:
            return False
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            return False
        try:
            ast.literal_eval(node.value)
            return True
        except Exception:
            return False
    

    @staticmethod
    def _display_name(name: str) -> str:
        return name.replace(" (global)", "")

    def _short(self, text: str) -> str:
        limit = self.compact.value_length * 2
        return text if len(text) <= limit else text[:limit - 3] + "..."

    def _clip(self, text: Optional[str]) -> Optional[str]:
        limit = self.compact.value_length
        if text is None or len(text) <= limit:
            return text
        marker = text.rfind("(len=")
        if marker != -1 and text.endswith((")]", ")}", "))")):         # a summarised big container: keep its length
            return text[:max(8, limit - (len(text) - marker) - 4)] + "... " + text[marker:]
        return text[:limit - 3] + "..."


    def _sequence(self, values: list[str]) -> str:
        """1,2,3 stays; 1,2,3,4,5 becomes 1..5; 7,7,7 becomes 7×3; long lists keep head and tail."""
        count = len(values)
        if count == 1:
            return values[0]
        if all(re.fullmatch(r"-?\d+", v) for v in values):
            numbers = [int(v) for v in values]
            steps = {b - a for a, b in zip(numbers, numbers[1:])}
            if count >= 4 and len(steps) == 1 and steps != {0}:
                step = steps.pop()
                return f"{numbers[0]}..{numbers[-1]}" + ("" if abs(step) == 1 else f" step {step}")
        if count >= 3 and len(set(values)) == 1:
            return f"{values[0]}x{count}"
        if count <= self.compact.sequence_plain:
            return self._run_length(values)
        head = values[:self.compact.sequence_head]
        tail = values[-self.compact.sequence_tail:]
        return f"{self._run_length(head)} ... {self._run_length(tail)} ({count} values)"


    @staticmethod
    def _run_length(values: list[str], identical_count: int = 10) -> str:
        """
        T,T,T,F -> Tx3,F.
        
        Args:
            values: A list of strings representing the values to be compressed.
            identical_count: The minimum number of identical consecutive values 
                required to trigger run-length encoding.
        
        Returns:
            A string representing the run-length encoded version of the input values.
        """
        pieces, index = [], 0
        while index < len(values):
            run = 1
            while index + run < len(values) and values[index + run] == values[index]:
                run += 1
            
            pieces.extend([f"{values[index]}x{run}"] 
                          if run >= identical_count 
                          else [values[index]] * run)
            index += run
        return ",".join(pieces)


def render_within_budget(structure: CodeStructure, roots: list[Invocation], 
                         result: Any, error: Optional[Exception],
                         expected: Optional[str], output: Optional[str], 
                         config: TraceConfig) -> str:
    """The trace, re-rendered with less detail (TraceConfig.tightened, then shorter notes) until it fits config.max_chars."""
    text = Renderer(structure, config).render(roots, result, error, expected, output)
    if config.max_chars is None or len(text) <= config.max_chars:
        return text
    for level in (1, 2, 3):
        text = Renderer(structure, config.tightened(level)).render(roots, result, error, expected, output)
        if len(text) <= config.max_chars:
            return text
    for note in (100, 60, 30):                                 # still too long: shorter notes. The code itself is never cut
        text = Renderer(structure, replace(config.tightened(3), max_note=note)).render(roots, result, error, expected, output)
        if len(text) <= config.max_chars:
            return text
    return cut_middle(text, int(config.max_chars * HARD_LIMIT_FACTOR))   # last resort, only for really long programs


def cut_middle(text: str, limit: int) -> str:
    """
    Keeps the first and the last lines and replaces the ones in between by one marker line, so that the result is at
    most `limit` characters. The start (the setup) and the end (where it went wrong, and the final outcome line) stay.
    Text that is short enough is returned unchanged.
    """
    if len(text) <= limit:
        return text
    lines = text.split("\n")
    room = limit - 60                                          # the marker line
    head, tail, used = [], [], 0
    for line in lines:                                         # about 60% of the room for the start
        if used + len(line) + 1 > room * 0.6:
            break
        head.append(line)
        used += len(line) + 1
    used = 0
    for line in reversed(lines[len(head):]):                   # the rest for the end, the last line always stays
        if used + len(line) + 1 > room * 0.4 and tail:
            break
        tail.append(line)
        used += len(line) + 1
    tail.reverse()
    omitted = len(lines) - len(head) - len(tail)
    return "\n".join(head + [f"... {omitted} lines omitted (size limit) ..."] + tail)
