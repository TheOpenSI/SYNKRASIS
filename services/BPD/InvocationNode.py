# Base Node.

from typing import Any

class InvocationNode:

    def __init__(self, func: str, depth: int):
        self.func     : str                  = func
        self.depth    : int                  = depth
        self.events   : list[dict[str, Any]] = []
        self.children : list[InvocationNode] = []
        self.pattern  : str                  = "unknown"


    def classify(self) -> str:
        """
        Classify the invocation pattern of this node based on its events and children.
            - simple: no loops, no recursion, no exceptions
            - loop: contains loops but no recursion or exceptions
            - recursive: contains recursive calls but no loops or exceptions
            - exception: raises an exception
            - mixed: contains a mix of loops, recursion, and/or exceptions
        """
        for child in self.children:
            child.classify()

        line_nums    = [e["line"] for e in self.events if e["event"] == "line"]
        has_loop     = len(line_nums) != len(set(line_nums))
        child_funcs  = [c.func for c in self.children]
        is_recursive = any(f == self.func for f in child_funcs)
        has_exception = any(e["event"] == "exception" for e in self.events)

        if has_exception:
            self.pattern = "exception"

        elif not self.children:
            self.pattern = "loop" if has_loop else "simple"

        elif is_recursive and has_loop:
            self.pattern = "mixed"

        elif is_recursive:
            self.pattern = "recursive"

        else:
            self.pattern = "loop" if has_loop else "simple"

        return self.pattern


    def print_tree(self, indent: int = 0) -> None:
        prefix     = "  " * indent
        call_event = next((e for e in self.events if e["event"] == "call"), None)
        args_str   = str(call_event["locals"]) if call_event else "{}"

        print(f"{prefix}func={self.func}  depth={self.depth}  pattern={self.pattern}  args={args_str}")

        for e in self.events:
            if e["event"] == "return":
                print(f"{prefix}  [RETURN]    {e['arg']}")
            elif e["event"] == "exception":
                exc_type, exc_value, _ = e["arg"]
                print(f"{prefix}  [EXCEPTION] {exc_type.__name__}: {exc_value}  locals={e['locals']}")

        for child in self.children:
            child.print_tree(indent + 1)