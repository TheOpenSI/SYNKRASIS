"""
Turns a runtime trace plus the static structure of the code into a plain
text narrative for an LLM: which lines ran, how each variable changed on
each line, how many times each loop ran and what happened per iteration,
which way each branch went, what every call returned, and where exceptions
came from. It is meant to stand in for a session at a debugger with a
breakpoint on every line.

The join between trace and structure is the line number: a step whose line
is a loop header opens or continues an iteration, a step whose line is an
`if` becomes a branch decision, a step on a return line becomes the return.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from services.BPD.parser.structure import BranchInfo, CodeStructure, FunctionInfo, LoopInfo
from services.BPD.tracer import Invocation, Step, safe_repr


@dataclass
class ReportConfig:
    max_iterations_shown: int = 12   # loops with more iterations show the first ones and the last few
    iterations_tail: int = 3
    max_call_depth: int = 8          # deeper calls are summarised as "called f(...) -> value"
    max_calls_per_step: int = 6      # a line that calls many traced functions lists this many
    max_value_length: int = 200      # longer reprs are truncated
    include_source: bool = True      # prefix the report with a numbered source listing
    indent: str = "  "


class ReportBuilder:

    def __init__(self, structure: CodeStructure, config: Optional[ReportConfig] = None) -> None:
        self.structure = structure
        self.config = config or ReportConfig()
        self._items_cache: dict[int, list[dict]] = {}
        self._executed: dict[int, FunctionInfo] = {}

    # -- public ---------------------------------------------------------------

    def build(self, call_description: str, roots: list[Invocation],
              result: Any, error: Optional[Exception]) -> str:
        self._items_cache = {}
        self._executed = {}
        body: list[str] = []
        for root in roots:
            body.extend(self._render_root(root))
            body.append("")

        lines = [f"Execution report for `{call_description}`"]
        if error is not None:
            lines.append(f"Outcome: raised {type(error).__name__}: {error}")
        else:
            lines.append(f"Outcome: returned {safe_repr(result, self.config.max_value_length)}")
        lines.append("")
        if self.config.include_source:
            lines.append("Source (line numbers below refer to this listing):")
            ranges = None
            if self.structure.from_file:
                ranges = [(f.first_line, f.end_line) for f in self._executed.values()]
            lines.extend(self.structure.listing(ranges))
            lines.append("")
        if not roots:
            lines.append("No traced function was called.")
            return "\n".join(lines)
        lines.append("Trace:")
        lines.extend(body)
        return "\n".join(lines).rstrip() + "\n"

    # -- analysis: steps -> items ----------------------------------------------
    #
    # Item kinds:
    #   stmt    {line, changes, calls, exception}
    #   branch  {line, outcome, values, calls, exception}
    #   return  {line, value, calls, changes, exception, implicit}
    #   loop    {line, loop, iterations: [{values, items}], after, exit, count}

    def _items_for(self, inv: Invocation) -> list[dict]:
        cached = self._items_cache.get(id(inv))
        if cached is None:
            cached = self._analyse(inv)
            self._items_cache[id(inv)] = cached
        return cached

    def _analyse(self, inv: Invocation) -> list[dict]:
        info = self.structure.function_for(inv.name, inv.first_line)
        if info is not None:
            self._executed[id(info)] = info
        loops = info.loops if info else {}
        branches = info.branches if info else {}
        return_lines = info.return_lines if info else None
        loop_targets = {t for loop in loops.values() for t in loop.targets}

        items: list[dict] = []
        stack: list[dict] = []   # open loops, outermost first
        steps = self._merge_repeated_steps(inv.steps, loops)
        previous: Optional[Step] = None
        saw_return = False

        def container() -> list[dict]:
            if not stack:
                return items
            top = stack[-1]
            if top["iteration"] is None:
                self._open_iteration(top, {}, -1)
            return top["iteration"]["items"]

        def push_loop(loop: LoopInfo, start: dict[str, str], headerless: bool) -> dict:
            entry = {
                "loop": loop,
                "item": {"kind": "loop", "line": loop.header_line, "loop": loop,
                         "iterations": [], "after": {}, "exit": None, "count": 0,
                         "start": start},
                "iteration": None,
                "opened_at": -1,
                "start": start,
                "headerless": headerless,
                "exclude": loop_targets,
            }
            container().append(entry["item"])
            stack.append(entry)
            return entry

        for index, step in enumerate(steps):
            following = steps[index + 1] if index + 1 < len(steps) else None

            # leaving a loop's line range without passing its header again = break or exception
            while stack and not stack[-1]["loop"].contains(step.line):
                reason = "exception" if previous is not None and previous.exception else "break"
                self._close_loop(stack.pop(), step.before, reason)

            # a body line of a loop that is not open: its header produced no line event
            # (e.g. `while True:` on older Pythons), so entering the body starts the loop
            for loop in sorted(loops.values(), key=lambda l: l.header_line):
                if loop.body_contains(step.line) and loop.header_line != step.line \
                        and not any(entry["loop"] is loop for entry in stack):
                    self._open_iteration(push_loop(loop, step.before, headerless=True), {}, index)
            top = stack[-1] if stack else None
            if top is not None and top["headerless"] and step.line == top["loop"].body_start \
                    and top["opened_at"] != index:
                self._open_iteration(top, {}, index)     # the body restarted: next iteration

            loop = loops.get(step.line)
            if loop is not None:
                self._handle_loop_header(loop, step, following, inv, stack, push_loop, container)
                previous = step
                continue

            returns_here = (following is None and inv.returned_normally
                            and inv.return_line == step.line
                            and (return_lines is None or step.line in return_lines))

            branch = branches.get(step.line)
            if branch is not None:
                container().append({
                    "kind": "branch",
                    "function": inv.name,
                    "line": step.line,
                    "outcome": True if returns_here else self._branch_outcome(branch, step, following, loops),
                    "values": {n: step.before[n] for n in branch.condition_names if n in step.before},
                    "calls": step.calls,
                    "exception": step.exception,
                    "value": inv.return_value if returns_here else None,
                    "returns": returns_here,
                })
                saw_return = saw_return or returns_here
                previous = step
                continue

            container().append({
                "kind": "return" if returns_here else "stmt",
                "function": inv.name,
                "line": step.line,
                "changes": step.changes(),
                "calls": step.calls,
                "exception": step.exception,
                "value": inv.return_value if returns_here else None,
                "implicit": False,
            })
            saw_return = saw_return or returns_here
            previous = step

        final_state = inv.final_state or (steps[-1].after if steps else {})
        while stack:
            self._close_loop(stack.pop(), final_state, "exception" if inv.raised else "return")

        if inv.returned_normally and not inv.is_generator and not saw_return:
            items.append({"kind": "return", "function": inv.name, "line": inv.return_line,
                          "changes": {}, "calls": [], "exception": None,
                          "value": inv.return_value, "implicit": True})
        return items

    def _handle_loop_header(self, loop: LoopInfo, step: Step, following: Optional[Step],
                            inv: Invocation, stack: list[dict], push_loop, container) -> None:
        if stack and stack[-1]["loop"] is loop:
            entry = stack[-1]
            entry["iteration"] = None          # the previous iteration ends at this header
        else:
            entry = push_loop(loop, step.before, headerless=False)

        header_activity = None
        if step.calls or step.exception:
            header_activity = {"kind": "stmt", "function": inv.name, "line": step.line,
                               "changes": {}, "calls": step.calls, "exception": step.exception}

        if following is not None and loop.body_contains(following.line) and not step.exception:
            if loop.kind == "for":
                values = {n: following.before[n] for n in loop.targets if n in following.before}
            else:
                values = {n: step.before[n] for n in loop.header_names if n in step.before}
            self._open_iteration(entry, values, -1)
            if header_activity:
                entry["iteration"]["items"].append(header_activity)
        else:
            state = following.before if following is not None else (inv.final_state or step.after)
            self._close_loop(stack.pop(), state, "exception" if step.exception else "completed")
            if header_activity:
                container().append(header_activity)

    @staticmethod
    def _open_iteration(entry: dict, values: dict[str, str], step_index: int) -> None:
        iteration = {"values": values, "items": []}
        entry["item"]["iterations"].append(iteration)
        entry["iteration"] = iteration
        entry["opened_at"] = step_index

    @staticmethod
    def _close_loop(entry: dict, state: dict[str, str], reason: str) -> None:
        item = entry["item"]
        loop: LoopInfo = entry["loop"]
        item["count"] = len(item["iterations"])
        item["exit"] = reason
        item["after"] = {
            name: value for name, value in state.items()
            if entry["start"].get(name) != value and name not in entry["exclude"]
        }
        entry["iteration"] = None

    @staticmethod
    def _merge_repeated_steps(steps: list[Step], loops: dict[int, LoopInfo]) -> list[Step]:
        """
        Consecutive events on one line that is not a loop line collapse into
        a single step. Python 3.12+ inlines comprehensions, so `[f(x) for x
        in xs]` fires one line event per element; older versions report it as
        one line and one hidden frame. Merging gives the same result on both.
        """
        protected = {loop.header_line for loop in loops.values()}
        protected |= {loop.body_start for loop in loops.values()}
        merged: list[Step] = []
        for step in steps:
            last = merged[-1] if merged else None
            if last is not None and last.line == step.line and step.line not in protected:
                merged[-1] = Step(line=last.line, before=last.before, after=step.after,
                                  calls=last.calls + step.calls,
                                  exception=step.exception or last.exception)
            else:
                merged.append(step)
        return merged

    @staticmethod
    def _branch_outcome(branch: BranchInfo, step: Step, following: Optional[Step],
                        loops: dict[int, LoopInfo]) -> Optional[bool]:
        if branch.body_start != branch.line:
            if following is None:
                return None
            return branch.in_body(following.line)
        # the body sits on the `if` line itself, so no separate line event says
        # whether it ran; infer it from where execution went next
        enclosing = [loop for loop in loops.values() if loop.contains(branch.line)]
        loop = max(enclosing, key=lambda l: l.header_line) if enclosing else None
        kind = branch.body_kind
        if kind == "return":
            return following is None and step.exception is None
        if kind == "break" and loop is not None:
            return following is None or not loop.contains(following.line)
        if kind == "continue" and loop is not None:
            if branch.line == loop.body_end:
                return None   # taken or not, execution goes back to the header
            return following is not None and following.line <= branch.line
        if step.changes() or step.calls:
            return True
        return None

    # -- rendering: items -> text ----------------------------------------------

    def _pad(self, indent: int, text: str) -> str:
        return self.config.indent * indent + text

    def _values(self, values: dict[str, Any]) -> str:
        return ", ".join(f"{k} = {v}" for k, v in values.items())

    def _changes(self, changes: dict[str, tuple[Optional[str], str]]) -> list[str]:
        return [f"{name} = {after}" if before is None else f"{name}: {before} -> {after}"
                for name, (before, after) in changes.items()]

    def _location(self, inv: Invocation) -> str:
        info = self.structure.function_for(inv.name, inv.first_line)
        if info is None:
            return ""
        return f"  [{info.qualname}, lines {info.def_line}-{info.end_line}]"

    def _render_root(self, inv: Invocation) -> list[str]:
        lines = [f"Call {inv.signature()}{self._location(inv)}"]
        lines.extend(self._render_body(inv, 1))
        return lines

    def _render_body(self, inv: Invocation, indent: int) -> list[str]:
        lines: list[str] = []
        for item in self._items_for(inv):
            lines.extend(self._render_item(item, indent))
        if inv.is_generator:
            yielded = ", ".join(inv.yields) if inv.yields else "nothing"
            lines.append(self._pad(indent, f"{inv.name} yielded {yielded}"))
        if inv.raised is not None:
            lines.append(self._pad(indent, f"Exception {inv.raised} propagated out of {inv.name}"
                                           f" (state: {self._values(inv.final_state) or 'no locals'})"))
        elif not inv.finished:
            lines.append(self._pad(indent, f"{inv.name} did not finish"))
        return lines

    def _is_inline(self, inv: Invocation) -> bool:
        """A call is shown on one line when nothing happened inside it worth a breakpoint."""
        if inv.depth > self.config.max_call_depth:
            return True
        if inv.is_generator or inv.raised is not None:
            return False
        interesting = 0
        for item in self._items_for(inv):
            if item["kind"] in ("loop", "branch") or item.get("exception"):
                return False
            if any(not self._is_inline(c) for c in item.get("calls", [])):
                return False
            if item.get("changes") or item.get("calls"):
                interesting += 1
        return interesting <= 1

    def _inline_call(self, inv: Invocation) -> str:
        text = f"called {inv.signature()}"
        if inv.raised is not None:
            return f"{text} -> raised {inv.raised}"
        if inv.is_generator:
            return f"{text} -> yielded {', '.join(inv.yields) if inv.yields else 'nothing'}"
        if inv.finished:
            text += f" -> {inv.return_value}"
        if inv.depth > self.config.max_call_depth:
            text += " (nested details omitted: depth limit)"
        return text

    def _render_child_block(self, inv: Invocation, indent: int) -> list[str]:
        lines = [self._pad(indent, f"called {inv.signature()}:{self._location(inv)}")]
        lines.extend(self._render_body(inv, indent + 1))
        return lines

    def _split_calls(self, calls: list[Invocation], exception) -> tuple[list[str], list[Invocation], list[str]]:
        """Inline call summaries, calls needing their own block, and an overflow note."""
        inline: list[str] = []
        nested: list[Invocation] = []
        shown = calls[: self.config.max_calls_per_step]
        for child in shown:
            if self._is_inline(child):
                inline.append(self._inline_call(child))
            else:
                nested.append(child)
        notes: list[str] = []
        hidden = len(calls) - len(shown)
        if hidden > 0:
            names = sorted({c.name for c in calls[len(shown):]})
            notes.append(f"... and {hidden} more calls to {', '.join(names)}")
        if exception is not None and not any(
                c.raised is not None and c.raised.identity == exception.identity for c in calls):
            notes.append(f"raised {exception}")
        return inline, nested, notes

    def _render_item(self, item: dict, indent: int) -> list[str]:
        kind = item["kind"]
        if kind == "loop":
            return self._render_loop(item, indent)

        source = self.structure.line_source(item["line"])
        if kind == "return" and item.get("implicit"):
            return [self._pad(indent, f"End of function reached: {item['function']} returned {item['value']}")]

        inline, nested, notes = self._split_calls(item.get("calls", []), item.get("exception"))
        head = f"Line {item['line']} `{source}`"
        tail: list[str] = []
        if kind == "branch":
            outcome = item["outcome"]
            verdict = "True" if outcome else ("False" if outcome is False else "evaluated (outcome not visible in trace)")
            head += f" was {verdict}"
            if item["values"]:
                head += f" ({self._values(item['values'])})"
            if item.get("returns"):
                tail.append(f"{item['function']} returned {item['value']}")
        else:
            tail.extend(self._changes(item.get("changes", {})))
            if kind == "return":
                tail.append(f"{item['function']} returned {item['value']}")

        if not nested:
            parts = inline + notes + tail
            if not parts and kind == "stmt":
                return []
            return [self._pad(indent, head + (": " + "; ".join(parts) if parts else ""))]

        lines = [self._pad(indent, head + (": " + "; ".join(inline) if inline else ":"))]
        for child in nested:
            lines.extend(self._render_child_block(child, indent + 1))
        if tail or notes:
            lines.append(self._pad(indent + 1, "; ".join(notes + tail)))
        return lines

    def _render_loop(self, item: dict, indent: int) -> list[str]:
        loop: LoopInfo = item["loop"]
        source = self.structure.line_source(item["line"])
        start_values = {n: item["start"][n] for n in loop.header_names if n in item["start"]}
        head = f"Line {item['line']} `{source}`"
        if start_values:
            head += f" ({self._values(start_values)})"
        count = item["count"]
        head += f" ran {count} iteration{'s' if count != 1 else ''}"
        if item["exit"] == "break":
            head += ", then exited via break"
        elif item["exit"] == "return":
            head += ", then returned from inside the loop"
        elif item["exit"] == "exception":
            head += ", then an exception left the loop"
        elif count == 0:
            head += " (body never executed)"
        lines = [self._pad(indent, head)]

        iterations = item["iterations"]
        shown: list[tuple[int, Optional[dict]]] = [(i, it) for i, it in enumerate(iterations, start=1)]
        if len(iterations) > self.config.max_iterations_shown:
            tail = self.config.iterations_tail
            head_count = self.config.max_iterations_shown - tail
            shown = shown[:head_count] + [(0, None)] + shown[len(iterations) - tail:]
        for number, iteration in shown:
            if iteration is None:
                omitted = len(iterations) - self.config.max_iterations_shown
                lines.append(self._pad(indent + 1, f"... {omitted} iterations omitted ..."))
                continue
            lines.extend(self._render_iteration(number, iteration, indent + 1))

        if item["exit"] in ("completed", "break"):
            after = self._values(item["after"]) or "no variables changed"
            lines.append(self._pad(indent + 1, f"After the loop: {after}"))
        return lines

    def _render_iteration(self, number: int, iteration: dict, indent: int) -> list[str]:
        label = f"Iteration {number}"
        if iteration["values"]:
            label += f" ({self._values(iteration['values'])})"
        rendered = [self._render_item(it, 0) for it in iteration["items"]]
        rendered = [r for r in rendered if r]
        if not rendered:
            return [self._pad(indent, f"{label}: no variable changes")]
        if len(rendered) <= 2 and all(len(r) == 1 for r in rendered):
            summary = "; ".join(r[0][0].lower() + r[0][1:] for r in rendered)
            return [self._pad(indent, f"{label}: {summary}")]
        lines = [self._pad(indent, f"{label}:")]
        for block in rendered:
            lines.extend(self._pad(indent + 1, line) for line in block)
        return lines
