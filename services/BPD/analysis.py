"""
Turns the raw steps of a trace (services.BPD.tracer) into a tree of items the renderer can use.

Item kinds, one per executed line (or per loop):
  stmt    {line, changes, calls, exception}
  branch  {line, outcome, values, calls, exception}
  return  {line, value, calls, changes, exception, implicit}
  loop    {line, loop, iterations: [{values, items}], after, exit, count}
The join between trace and code structure is the line number: a step on a loop header opens or
continues an iteration, a step on an `if` becomes a branch outcome, a step on a return line the return.
"""
from __future__ import annotations

from typing import Optional

from services.BPD.structure import BranchInfo, CodeStructure, LoopInfo
from services.BPD.tracer import Invocation, Step


class Analyser:

    def __init__(self, structure: CodeStructure, max_call_depth: int = 3) -> None:
        self.structure = structure
        self.max_call_depth = max_call_depth
        self._items_cache: dict[int, list[dict]] = {}

    def _items_for(self, inv: Invocation) -> list[dict]:
        cached = self._items_cache.get(id(inv))
        if cached is None:
            cached = self._analyse(inv)
            self._items_cache[id(inv)] = cached
        return cached

    def _analyse(self, inv: Invocation) -> list[dict]:
        info = self.structure.function_for(inv.name, inv.first_line)
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

    def is_inline(self, inv: Invocation) -> bool:
        """A call is shown on one line when nothing happened inside it worth a breakpoint."""
        if inv.depth > self.max_call_depth:
            return True
        if inv.is_generator or inv.raised is not None:
            return False
        interesting = 0
        for item in self._items_for(inv):
            if item["kind"] in ("loop", "branch") or item.get("exception"):
                return False
            if any(not self.is_inline(c) for c in item.get("calls", [])):
                return False
            if item.get("changes") or item.get("calls"):
                interesting += 1
        return interesting <= 1
