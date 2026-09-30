from typing import Any
from InvocationNode import InvocationNode

class TraceAnalyser:

    def build_tree(self, log: list[dict[str, Any]]) -> list[InvocationNode]:
        roots : list[InvocationNode] = []
        stack : list[InvocationNode] = []

        for entry in log:
            event = entry["event"]

            if event == "call":
                depth = len(stack) + 1
                node  = InvocationNode(func=entry["func"], depth=depth)
                node.events.append(entry)

                if stack:
                    stack[-1].children.append(node)
                else:
                    roots.append(node)

                stack.append(node)

            elif event in ("line", "exception"):
                if stack:
                    stack[-1].events.append(entry)

            elif event == "return":
                if stack:
                    stack[-1].events.append(entry)
                    stack.pop()

        return roots

    def analyse(self, log: list[dict[str, Any]]) -> list[InvocationNode]:
        roots = self.build_tree(log)
        for root in roots:
            root.classify()
        return roots

    def print_analysis(self, roots: list[InvocationNode]) -> None:
        for root in roots:
            root.print_tree()
