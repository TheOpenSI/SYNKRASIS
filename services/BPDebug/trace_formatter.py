from typing import Any


class TraceFormatter:

    def format(self, summary: dict[str, Any], indent: int = 0) -> str:
        pattern = summary["pattern"]

        if pattern == "simple":
            return self._format_simple(summary, indent)
        elif pattern == "loop":
            return self._format_loop(summary, indent)
        elif pattern == "recursive":
            return self._format_recursive(summary, indent)
        elif pattern == "exception":
            return self._format_exception(summary, indent)
        elif pattern == "mixed":
            return self._format_mixed(summary, indent)
        else:
            return self._pad(indent, f"{summary['func']} was called but could not be analysed.")


    def _pad(self, indent: int, text: str) -> str:
        prefix = "  " * indent
        return "\n".join(prefix + line for line in text.splitlines())


    def _format_args(self, args: dict[str, Any]) -> str:
        if not args:
            return "no arguments"
        return " and ".join(f"{k}={v}" for k, v in args.items())


    def _format_locals(self, locals_: dict[str, Any]) -> str:
        return " and ".join(f"{k}={v}" for k, v in locals_.items())


    def _format_simple(self, summary: dict[str, Any], indent: int) -> str:
        func   = summary["func"]
        args   = self._format_args(summary["args"])
        ret    = summary["return"]
        lines  = [f"{func} was called with {args} and returned {ret}."]
        return self._pad(indent, "\n".join(lines))


    def _format_loop(self, summary: dict[str, Any], indent: int) -> str:
        func       = summary["func"]
        args       = self._format_args(summary["args"])
        iterator   = summary["iterator"]
        accumulators = summary["accumulators"]
        iterations = summary["iterations"]
        ret        = summary["return"]
        children   = summary.get("children", [])

        lines = [f"{func} was called with {args}."]

        if iterator:
            lines.append(f"The function contains a loop iterating over {iterator}.")
            for i, it in enumerate(iterations):
                iter_val  = it.get(iterator, "unknown")
                acc_parts = []
                for acc in accumulators:
                    before = it.get(f"{acc}_before")
                    after  = it.get(f"{acc}_after")
                    if before is not None or after is not None:
                        acc_parts.append(f"{acc} changed from {before} to {after}")
                acc_str = " and ".join(acc_parts) if acc_parts else "no accumulator changes"
                lines.append(f"In iteration {i + 1}, {iterator} was {iter_val} and {acc_str}.")

        child_narratives = []
        for child in children:
            child_narratives.append(self.format(child, indent=0))
        if child_narratives:
            lines.append("The following helper calls were made during the loop:")
            lines.extend(child_narratives)

        lines.append(f"The function returned {ret}.")
        return self._pad(indent, "\n".join(lines))


    def _format_recursive(self, summary: dict[str, Any], indent: int) -> str:
        func     = summary["func"]
        args     = self._format_args(summary["args"])
        ret      = summary["return"]
        children = summary.get("children", [])

        lines = [f"{func} was called with {args}."]

        if children:
            child = children[0]
            child_args = self._format_args(child["args"])
            if child["pattern"] == "simple":
                lines.append(
                    f"This was the base case. It returned {child['return']}."
                )
            else:
                lines.append(
                    f"It called {child['func']} again with {child_args}."
                )
                nested = self._format_recursive(child, indent=0)
                for line in nested.splitlines()[1:]:
                    lines.append("  " + line)

        lines.append(f"The function returned {ret}.")
        return self._pad(indent, "\n".join(lines))


    def _format_exception(self, summary: dict[str, Any], indent: int) -> str:
        func      = summary["func"]
        args      = self._format_args(summary["args"])
        exc       = summary.get("exception")
        children  = summary.get("children", [])

        lines = [f"{func} was called with {args}."]

        for child in children:
            if child["pattern"] == "simple":
                child_args = self._format_args(child["args"])
                lines.append(
                    f"It called {child['func']} with {child_args}, "
                    f"which returned {child['return']}."
                )
            elif child["pattern"] == "exception":
                child_args = self._format_args(child["args"])
                child_exc  = child.get("exception", {})
                lines.append(
                    f"It then called {child['func']} with {child_args}."
                )
                lines.append(
                    f"Inside {child['func']}, a {child_exc.get('type')} was raised: "
                    f"{child_exc.get('message')}."
                )
                lines.append(
                    f"At the point of failure the local variables were "
                    f"{self._format_locals(child_exc.get('locals', {}))}."
                )

        if exc:
            lines.append(f"The exception propagated back to {func}.")
            lines.append(
                f"At that point the local variables were "
                f"{self._format_locals(exc.get('locals', {}))}."
            )

        return self._pad(indent, "\n".join(lines))


    def _format_mixed(self, summary: dict[str, Any], indent: int) -> str:
        func       = summary["func"]
        args       = self._format_args(summary["args"])
        loop       = summary.get("loop", {})
        iterator   = loop.get("iterator")
        accumulators = loop.get("accumulators", [])
        iterations = loop.get("iterations", [])
        children   = summary.get("children", [])
        ret        = summary["return"]

        lines = [f"{func} was called with {args}."]

        if iterator:
            lines.append(f"The function contains a loop iterating over {iterator}.")
            for i, it in enumerate(iterations):
                iter_val  = it.get(iterator, "unknown")
                acc_parts = []
                for acc in accumulators:
                    before = it.get(f"{acc}_before")
                    after  = it.get(f"{acc}_after")
                    if before is not None or after is not None:
                        acc_parts.append(f"{acc} changed from {before} to {after}")
                acc_str = " and ".join(acc_parts) if acc_parts else "no accumulator changes"
                lines.append(f"In iteration {i + 1}, {iterator} was {iter_val} and {acc_str}.")

        for child in children:
            child_args = self._format_args(child["args"])
            lines.append(f"It then called {child['func']} again with {child_args}.")
            nested = self.format(child, indent=0)
            for line in nested.splitlines()[1:]:
                lines.append("  " + line)

        lines.append(f"The function returned {ret}.")
        return self._pad(indent, "\n".join(lines))