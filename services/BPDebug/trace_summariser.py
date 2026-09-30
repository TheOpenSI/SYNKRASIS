from typing import Any
from TraceAnalyser import InvocationNode


class TraceSummariser:

    def summarise(self, node: InvocationNode) -> dict[str, Any]:
        pattern = node.pattern

        if pattern == "simple":
            return self._summarise_simple(node)
        elif pattern == "loop":
            return self._summarise_loop(node)
        elif pattern == "recursive":
            return self._summarise_recursive(node)
        elif pattern == "exception":
            return self._summarise_exception(node)
        elif pattern == "mixed":
            return self._summarise_mixed(node)
        else:
            return {"pattern": "unknown", "func": node.func}


    def _get_args(self, node: InvocationNode) -> dict[str, Any]:
        call_event = next((e for e in node.events if e["event"] == "call"), None)
        return call_event["locals"].copy() if call_event else {}


    def _get_return(self, node: InvocationNode) -> Any:
        return_event = next((e for e in node.events if e["event"] == "return"), None)
        return return_event["arg"] if return_event else None


    def _get_exception(self, node: InvocationNode) -> dict[str, Any] | None:
        exc_event = next((e for e in node.events if e["event"] == "exception"), None)
        if exc_event is None:
            return None
        exc_type, exc_value, _ = exc_event["arg"]
        return {
            "type"    : exc_type.__name__,
            "message" : str(exc_value),
            "locals"  : exc_event["locals"].copy(),
        }


    def _detect_loop_structure(
        self, node: InvocationNode
    ) -> tuple[str | None, list[str], list[dict[str, Any]]]:
        initial_locals = set(self._get_args(node).keys())
        line_events    = [e for e in node.events if e["event"] == "line"]

        line_nums      = [e["line"] for e in line_events]
        if not line_nums:
            return None, [], []

        loop_line      = next(
            (ln for ln in line_nums if line_nums.count(ln) > 1), None
        )
        if loop_line is None:
            return None, [], []

        loop_indices   = [i for i, e in enumerate(line_events) if e["line"] == loop_line]
        iterations     = []

        for idx, start in enumerate(loop_indices):
            end        = loop_indices[idx + 1] if idx + 1 < len(loop_indices) else len(line_events)
            slice_     = line_events[start:end]

            all_locals = {}
            for e in slice_:
                all_locals.update(e["locals"])

            iterations.append(all_locals)

        if not iterations:
            return None, [], []

        # iterator — the variable Python assigns at the for-loop header
        # identified as the variable that first appears in locals AT the
        # loop header line, i.e. absent in the event just before the loop
        header_events    = [e for e in line_events if e["line"] == loop_line]
        first_header_idx = next(
            i for i, e in enumerate(line_events) if e["line"] == loop_line
        )
        pre_loop_locals  = (
            set(line_events[first_header_idx - 1]["locals"].keys())
            if first_header_idx > 0
            else initial_locals
        )

        iterator = next(
            (k for k in header_events[0]["locals"] if k not in pre_loop_locals),
            None
        )

        static_keys    = {
            k for k in iterations[0]
            if all(it.get(k) == iterations[0][k] for it in iterations)
        }

        accumulators   = [
            k for k in iterations[0]
            if k != iterator and k not in static_keys
        ]

        cleaned        = []
        for i, it in enumerate(iterations):
            entry      = {}
            if iterator and iterator in it:
                entry[iterator] = it[iterator]
            for acc in accumulators:
                if acc in it:
                    before_val = iterations[i - 1].get(acc) if i > 0 else self._get_args(node).get(acc)
                    entry[f"{acc}_before"] = before_val
                    entry[f"{acc}_after"]  = it[acc]
            cleaned.append(entry)

        return iterator, accumulators, cleaned


    def _summarise_simple(self, node: InvocationNode) -> dict[str, Any]:
        return {
            "pattern" : "simple",
            "func"    : node.func,
            "args"    : self._get_args(node),
            "return"  : self._get_return(node),
        }


    def _summarise_loop(self, node: InvocationNode) -> dict[str, Any]:
        iterator, accumulators, iterations = self._detect_loop_structure(node)
        children = [self.summarise(c) for c in node.children]

        return {
            "pattern"      : "loop",
            "func"         : node.func,
            "args"         : self._get_args(node),
            "iterator"     : iterator,
            "accumulators" : accumulators,
            "iterations"   : iterations,
            "return"       : self._get_return(node),
            "children"     : children,
        }


    def _summarise_recursive(self, node: InvocationNode) -> dict[str, Any]:
        children = [self.summarise(c) for c in node.children]

        return {
            "pattern"  : "recursive",
            "func"     : node.func,
            "args"     : self._get_args(node),
            "return"   : self._get_return(node),
            "children" : children,
        }


    def _summarise_exception(self, node: InvocationNode) -> dict[str, Any]:
        children = [self.summarise(c) for c in node.children]

        return {
            "pattern"   : "exception",
            "func"      : node.func,
            "args"      : self._get_args(node),
            "return"    : None,
            "exception" : self._get_exception(node),
            "children"  : children,
        }


    def _summarise_mixed(self, node: InvocationNode) -> dict[str, Any]:
        iterator, accumulators, iterations = self._detect_loop_structure(node)
        children = [self.summarise(c) for c in node.children]

        return {
            "pattern"  : "mixed",
            "func"     : node.func,
            "args"     : self._get_args(node),
            "return"   : self._get_return(node),
            "loop"     : {
                "iterator"     : iterator,
                "accumulators" : accumulators,
                "iterations"   : iterations,
            },
            "children" : children,
        }