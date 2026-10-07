"""
Compact execution trace for an LLM: the code that ran, with the runtime values written next to it.

    for n in nums:            # 4 iterations; n=1..4
        if is_even(n):        # F,T,F,T
            count += 1        # count=1,2  (iters 2,4)

Rules (the whole format):
  1. Only lines that executed are shown, in source order, indented like the source. The model has
     the code, so no line numbers and no explanations, just the source text of the line.
  2. A line that ran many times (loop body, repeated call) is ONE row, its values are sequences:
     `count=1,2`, `n=1..4`, branch outcomes `F,T,F,T`. Runs of 3+ equal values become `F×4`.
  3. A row that ran in only some iterations says which: `(iters 2,4)`. That is how the iteration
     that breaks the pattern shows up, e.g. `return -1  # -1  (iters 5)`.
  4. Long sequences keep the first and last values: `0,1,2,3 ... 98,99 (100 values)`.
  5. Lists and dicts are shown as the change, not the whole value: `X[0..4]=1,1,2,3,2`, `queries += (1, 4)`.
  6. Nothing is printed for lines that tell nothing, like `total = 0` (the value is in the code).
  7. A call to a traced function: only the return values when they say something; a call with
     real logic inside gets its own indented block (first call only, the rest as return values).

The analysis (what happened in which loop, branch, call) is the one of services.BPD.report; only the
rendering is new.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, replace
from typing import Any, Optional

from services.BPD.parser.structure import CodeStructure
from services.BPD.report import ReportBuilder, ReportConfig
from services.BPD.tracer import Invocation

SEPARATOR = "  # "


@dataclass
class CompactConfig:
    sequence_plain: int = 6        # sequences up to this long are written out completely
    sequence_head: int = 4         # longer ones keep this many values at the start ...
    sequence_tail: int = 2         # ... and this many at the end
    value_length: int = 40         # longer values are clipped
    line_length: int = 70          # longer source lines are clipped
    max_call_depth: int = 3        # deeper calls are summarised by their return value
    max_chars: Optional[int] = 6000

    def tightened(self, level: int) -> "CompactConfig":
        """Less detail, level 1, 2, 3, used when the trace is over max_chars."""
        plain, head, tail, length, depth = [(5, 3, 2, 30, 2), (4, 2, 1, 24, 2), (3, 2, 1, 16, 1)][min(level, 3) - 1]
        return replace(self, sequence_plain=plain, sequence_head=head, sequence_tail=tail,
                       value_length=length, max_call_depth=depth)


@dataclass
class Row:
    """One source line, with every time it executed."""
    line: int
    kind: str                                    # "stmt", "branch", "return" or "loop"
    executions: list[dict]                       # the analysed items (see ReportBuilder._analyse), one per time
    iteration_ids: list[Optional[int]]           # enclosing loop iteration of each execution (None: not in a loop)
    children: list["Row"]                        # loops: the rows of the loop body
    loop_runs: list[dict]                        # loops: the loop items (a nested loop runs once per outer iteration)
    iterations_total: int = 0                    # loops: iterations over all runs


class CompactReportBuilder(ReportBuilder):

    def __init__(self, structure: CodeStructure, config: Optional[CompactConfig] = None) -> None:
        self.compact = config or CompactConfig()
        super().__init__(structure, ReportConfig(max_call_depth=self.compact.max_call_depth,
                                                 display_value_length=self.compact.value_length,
                                                 hide_noise_values=True))

    # -- entry --------------------------------------------------------------------------------

    def build_compact(self, roots: list[Invocation], result: Any, error: Optional[Exception],
                      expected: Optional[str] = None, output: Optional[str] = None) -> str:
        """
        The trace, then one final line with the outcome. expected: the expected answer (public tests
        only). output: what a stdin program printed, when given it replaces the returned value.
        """
        self._items_cache = {}
        lines: list[str] = []
        self._roots = roots
        for root in roots:
            lines.extend(self._render_invocation(root, level=0, is_root=True))
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

    # -- one call -------------------------------------------------------------------------------

    def _render_invocation(self, inv: Invocation, level: int, is_root: bool = False,
                           hide_header: bool = False) -> list[str]:
        info = self.structure.function_for(inv.name, inv.first_line)
        rows = self._build_rows([(None, self._items_for(inv))], info)
        lines: list[str] = []
        hidden_main = inv.name == "__bpd_main__" or hide_header   # __bpd_main__: wrapper used for stdin programs
        if not hidden_main:
            lines.append(self._indent(level, f"{self._signature_compact(inv, nested=not is_root)}:"))
        body_level = level if hidden_main else level + 1
        lines.extend(self._render_rows(rows, body_level, total_iterations=None, call=inv))
        if inv.finished and inv.raised is None and not hidden_main and not self._returned_explicitly(inv):
            if inv.return_value not in (None, "None"):
                lines.append(self._indent(body_level, f"returned {self._short(inv.return_value)}"))
        return lines

    def _returned_explicitly(self, inv: Invocation) -> bool:
        return any((item["kind"] == "return" and not item.get("implicit")) or item.get("returns")
                   for item in self._items_for(inv))

    def _signature_compact(self, inv: Invocation, nested: bool = False) -> str:
        """name(arg=value, ...). In nested calls long values (a big list passed down again and again) are left out."""
        arguments = ", ".join(f"{name}={self._clip(value)}" for name, value in inv.args.items()
                              if name != "self" and not self._is_noise(value)
                              and not (nested and len(value) > self.compact.value_length))
        return f"{inv.name}({arguments})"

    # -- rows: merge the executions of every source line ------------------------------------------

    def _build_rows(self, groups: list[tuple[Optional[int], list[dict]]], info=None) -> list[Row]:
        """
        groups: (iteration id, items executed in it). Returns one Row per source line, in source order.
        info: FunctionInfo of the function, used to put an `else:` line before code that ran in an else branch
        (the tracer reports no line for `else:` itself, so without it that code would look like part of the `if`).
        """
        by_line: dict[int, Row] = {}
        for iteration_id, items in groups:
            for item in items:
                if item.get("implicit"):
                    continue                                        # "end of function reached", shown by the caller
                row = by_line.setdefault(item["line"], Row(item["line"], item["kind"], [], [], [], []))
                if item["kind"] == "loop":
                    row.loop_runs.append(item)
                row.executions.append(item)
                row.iteration_ids.append(iteration_id)
        for row in by_line.values():
            if row.kind == "loop":
                pooled = [(number, iteration["items"])
                          for number, iteration in enumerate(self._all_iterations(row), start=1)]
                row.iterations_total = len(pooled)
                row.children = self._build_rows(pooled, info)
        if info is not None:
            for row in list(by_line.values()):
                branch = info.branches.get(row.line) if row.kind == "branch" else None
                else_line = self._else_line(branch) if branch is not None else None
                if else_line is not None and else_line not in by_line and any(
                        branch.in_orelse(line) for line in by_line):
                    by_line[else_line] = Row(else_line, "marker", [], [], [], [])
        return [by_line[line] for line in sorted(by_line)]

    def _else_line(self, branch) -> Optional[int]:
        """Line number of the `else:` that belongs to an if, None when it has no else or an elif."""
        if branch.orelse_start is None:
            return None
        for line in range(branch.orelse_start, max(branch.orelse_start - 4, 0), -1):
            if re.match(r"^else\s*:", self.structure.line_source(line)):
                return line
        return None

    @staticmethod
    def _all_iterations(row: Row) -> list[dict]:
        return [iteration for run in row.loop_runs for iteration in run["iterations"]]

    # -- rendering rows ---------------------------------------------------------------------------

    def _render_rows(self, rows: list[Row], level: int, total_iterations: Optional[int], call: Invocation) -> list[str]:
        if not rows:
            return []
        indents = sorted({self._indent_of(row.line) for row in rows})
        rank = {value: index for index, value in enumerate(indents)}
        lines: list[str] = []
        for row in rows:
            lines.extend(self._render_row(row, level + rank[self._indent_of(row.line)], total_iterations, call))
        return lines

    def _render_row(self, row: Row, level: int, total_iterations: Optional[int], call: Invocation) -> list[str]:
        if row.kind == "marker":
            return [self._indent(level, "else:")]
        if row.kind == "loop":
            parts = self._loop_parts(row)
            nested_blocks: list[list[str]] = []
        else:
            parts, nested_blocks = self._statement_parts(row, level, call)

        if not parts and not nested_blocks:
            return []

        source = self._clip_line(self.structure.line_source(row.line))
        text = source + (SEPARATOR + "; ".join(parts) if parts else "")
        sparse = self._sparse_note(row, total_iterations)
        if sparse:
            text += "  " + sparse                  # a note about the row, apart from its values
        lines = [self._indent(level, text)]
        for block in nested_blocks:
            lines.extend(block)
        if row.kind == "loop":
            lines.extend(self._render_rows(row.children, level + 1, row.iterations_total, call))
        return lines

    # -- loops ------------------------------------------------------------------------------------

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

    # -- everything else ----------------------------------------------------------------------------

    def _statement_parts(self, row: Row, level: int, call: Invocation) -> tuple[list[str], list[list[str]]]:
        executions = row.executions
        parts: list[str] = []

        if row.kind == "branch" or any(e["kind"] == "branch" for e in executions):
            parts.append(self._branch_part(executions, call))

        changes = {}
        if not self._is_literal_assignment(self.structure.line_source(row.line)):
            for execution in executions:
                for name, (before, after) in execution.get("changes", {}).items():
                    if not self._is_noise(after):
                        changes.setdefault(name, []).append((before, after))
        has_nested = any(not self._is_inline(c) for e in executions for c in e.get("calls", []) if not c.name.startswith("<"))
        if has_nested:      # a callee changed a list/dict: its own block shows how, do not repeat it here
            changes = {n: p for n, p in changes.items() if not all(self._is_container_change(b, a) for b, a in p)}
        change_texts = [self._variable_part(name, pairs) for name, pairs in changes.items()]
        parts.extend(text for text in change_texts if text)

        returned = [e["value"] for e in executions if e.get("value") is not None and (e["kind"] == "return" or e.get("returns"))]
        if returned and call in self._roots:
            # the final line has the value; only say which return ran when there are several
            info = self.structure.function_for(call.name, call.first_line)
            if info is not None and len(info.return_lines) > 1:
                parts.append("returned")
        elif returned:
            parts.append("returns " + self._sequence([self._clip(v) for v in returned]))

        call_part, nested_blocks = self._call_parts(row, level, changes, call)
        if call_part:
            parts.append(call_part)

        for execution in executions:
            exception = execution.get("exception")
            if exception is not None and not self._raised_inside_call(execution):
                parts.append(f"raised {exception}")
                break
        return parts, nested_blocks

    def _branch_part(self, executions: list[dict], call: Invocation) -> str:
        """
        Outcomes as T/F. Values of the condition are added only when they tell something new: not the
        arguments already in the call header, and for repeated branches only short values that never
        change (the ones that change are the loop variables or the rows above).
        """
        branches = [e for e in executions if e["kind"] == "branch"]
        outcomes = ["T" if e.get("outcome") else "F" if e.get("outcome") is False else "?" for e in branches]
        names = list(dict.fromkeys(name for e in branches for name in e.get("values", {})))
        shown = []
        for name in names:
            values = [e["values"][name] for e in branches if name in e.get("values", {})]
            if self._is_noise(values[0]) or call.args.get(name) == values[0] and len(set(values)) == 1:
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

    def _call_parts(self, row: Row, level: int, changes: dict, call: Invocation) -> tuple[str, list[list[str]]]:
        calls = [c for e in row.executions for c in e.get("calls", []) if not c.name.startswith("<")]
        if not calls:
            return "", []
        inline = [c for c in calls if self._is_inline(c)]
        nested = [c for c in calls if not self._is_inline(c)]
        text = ""
        if inline:
            text = self._inline_calls_text(inline, row, changes)
        blocks: list[list[str]] = []
        if nested:
            first = nested[0]
            extra = f"  [first of {len(nested)} calls]" if len(nested) > 1 else ""
            call_only = self.structure.line_source(row.line) == f"{first.name}()" and not first.args
            block = self._render_invocation(first, level + 1, hide_header=call_only)
            if extra and block:
                block[0] += extra
            blocks.append(block)
            if len(nested) > 1:
                returned = [self._clip(c.return_value or "?") for c in nested]
                if not all(r == "None" for r in returned) and not any(returned == [self._clip(after) for _, after in pairs] for pairs in changes.values()):
                    text = (text + "; " if text else "") + f"{first.name} returns {self._sequence(returned)}"
        return text, blocks

    def _inline_calls_text(self, inline: list[Invocation], row: Row, changes: dict) -> str:
        pieces = []
        for name in dict.fromkeys(c.name for c in inline):
            group = [c for c in inline if c.name == name]
            returns = [self._clip(c.return_value if c.raised is None else f"raised {c.raised}") for c in group]
            if all(r == "None" for r in returns):
                continue                                           # nothing returned: nothing to say
            all_bool = all(r in ("True", "False") for r in returns)
            if row.kind == "branch" and all_bool:
                continue                                           # the branch outcome already says it
            if any(returns == [self._clip(after) for _, after in pairs] for pairs in changes.values()):
                continue                                           # `x = f(y)`: x=... says it
            if len(group) == 1:
                pieces.append(f"{self._signature_compact(group[0])} -> {returns[0]}")
            else:
                pieces.append(f"{name} returns {self._sequence(returns)}")
        return "; ".join(pieces)

    @staticmethod
    def _raised_inside_call(execution: dict) -> bool:
        exception = execution.get("exception")
        return exception is not None and any(c.raised is not None and c.raised.identity == exception.identity
                                             for c in execution.get("calls", []))

    # -- small helpers --------------------------------------------------------------------------------

    def _sparse_note(self, row: Row, total_iterations: Optional[int]) -> str:
        """
        Says in which iterations of the enclosing loop the line ran, when it was not all of them:
        `(iters 2,4)`, or for a line that skipped a few `(not in iters 2)`, or `(30 of 120 iters)`.
        """
        if total_iterations is None:
            return ""
        ran = sorted({i for i in row.iteration_ids if i is not None})
        if not ran or len(ran) == total_iterations:
            return ""
        skipped = [i for i in range(1, total_iterations + 1) if i not in set(ran)]
        if len(skipped) <= 3 and len(skipped) < len(ran):
            return f"(not in iters {','.join(map(str, skipped))})"
        if len(ran) <= 4:
            return f"(iters {','.join(map(str, ran))})"
        return f"({len(ran)} of {total_iterations} iters)"

    @staticmethod
    def _is_literal_assignment(source: str) -> bool:
        """`total = 0`, `seen = []`: the value is in the code, a trace row would say nothing."""
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

    def _indent_of(self, line: int) -> int:
        text = self.structure.lines[line - 1] if 1 <= line <= len(self.structure.lines) else ""
        return len(text) - len(text.lstrip())

    @staticmethod
    def _indent(level: int, text: str) -> str:
        return "  " * level + text

    @staticmethod
    def _display_name(name: str) -> str:
        return name.replace(" (global)", "")

    def _short(self, text: str) -> str:
        limit = self.compact.value_length * 2
        return text if len(text) <= limit else text[:limit - 3] + "..."

    def _clip_line(self, text: str) -> str:
        limit = self.compact.line_length
        return text if len(text) <= limit else text[:limit - 3] + "..."

    def _clip(self, text: Optional[str]) -> Optional[str]:
        limit = self.compact.value_length
        if text is None or len(text) <= limit:
            return text
        return text[:limit - 3] + "..."

    # -- sequences ---------------------------------------------------------------------------------------

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
            return f"{values[0]}×{count}"
        if count <= self.compact.sequence_plain:
            return self._run_length(values)
        head = values[:self.compact.sequence_head]
        tail = values[-self.compact.sequence_tail:]
        return f"{self._run_length(head)} ... {self._run_length(tail)} ({count} values)"

    @staticmethod
    def _run_length(values: list[str]) -> str:
        """T,T,T,F -> T×3,F (runs of 3 or more only)."""
        pieces, index = [], 0
        while index < len(values):
            run = 1
            while index + run < len(values) and values[index + run] == values[index]:
                run += 1
            pieces.extend([f"{values[index]}×{run}"] if run >= 3 else [values[index]] * run)
            index += run
        return ",".join(pieces)
