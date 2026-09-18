"""
Static structure of a block of Python code, taken from its AST.

Only the facts the report needs are kept: where every function lives and,
inside each function, where its loops, branches and return statements are.
Line numbers are the join key between this structure and the runtime trace,
so each construct records the line range it occupies.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Optional


def _names_in(node: Optional[ast.AST]) -> list[str]:
    """Distinct variable names appearing anywhere inside an expression."""
    if node is None:
        return []
    names: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id not in names:
            names.append(child.id)
    return names


def _end_line(statements: list[ast.stmt]) -> int:
    return max(getattr(stmt, "end_lineno", stmt.lineno) for stmt in statements)


def _body_kind(body: list[ast.stmt]) -> str:
    if len(body) != 1:
        return "other"
    return {ast.Return: "return", ast.Break: "break", ast.Continue: "continue"}.get(type(body[0]), "other")


@dataclass
class LoopInfo:
    kind: str                 # "for" or "while"
    header_line: int
    body_start: int
    body_end: int
    targets: list[str]        # loop variables of a "for"; empty for "while"
    header_names: list[str]   # names used in the iterable or the condition

    def contains(self, line: int) -> bool:
        return self.header_line <= line <= self.body_end

    def body_contains(self, line: int) -> bool:
        return self.body_start <= line <= self.body_end


@dataclass
class BranchInfo:
    line: int
    body_start: int
    body_end: int
    orelse_start: Optional[int]
    orelse_end: Optional[int]
    condition_names: list[str]
    body_kind: str = "other"   # "return", "break", "continue" or "other": what a one-statement body does

    def in_body(self, line: int) -> bool:
        return self.body_start <= line <= self.body_end

    def in_orelse(self, line: int) -> bool:
        return self.orelse_start is not None and self.orelse_start <= line <= self.orelse_end


@dataclass
class FunctionInfo:
    name: str
    qualname: str
    first_line: int           # decorator line if decorated, else the def line (== code.co_firstlineno)
    def_line: int
    end_line: int
    parameters: list[str]
    loops: dict[int, LoopInfo] = field(default_factory=dict)        # keyed by header line
    branches: dict[int, BranchInfo] = field(default_factory=dict)   # keyed by the if/elif line
    return_lines: set[int] = field(default_factory=set)
    global_names: set[str] = field(default_factory=set)
    comprehension_names: set[str] = field(default_factory=set)   # loop variables of comprehensions


class _FunctionScanner:
    """
    Records the loops, branches, returns and global declarations that belong
    directly to one function body. Nested function and class definitions are
    skipped: they run in their own frames and get their own FunctionInfo.
    """

    def __init__(self, info: FunctionInfo) -> None:
        self.info = info

    def scan(self, node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                self._scan_statement(child)
            elif not isinstance(child, ast.expr):
                # except handlers, match cases, with-items: may hold statements
                self.scan(child)

    def _scan_statement(self, node: ast.stmt) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return
        if isinstance(node, (ast.For, ast.AsyncFor)):
            self.info.loops[node.lineno] = LoopInfo(
                kind="for",
                header_line=node.lineno,
                body_start=node.body[0].lineno,
                body_end=_end_line(node.body),
                targets=_names_in(node.target),
                header_names=_names_in(node.iter),
            )
        elif isinstance(node, ast.While):
            self.info.loops[node.lineno] = LoopInfo(
                kind="while",
                header_line=node.lineno,
                body_start=node.body[0].lineno,
                body_end=_end_line(node.body),
                targets=[],
                header_names=_names_in(node.test),
            )
        elif isinstance(node, ast.If):
            self.info.branches[node.lineno] = BranchInfo(
                line=node.lineno,
                body_start=node.body[0].lineno,
                body_end=_end_line(node.body),
                orelse_start=node.orelse[0].lineno if node.orelse else None,
                orelse_end=_end_line(node.orelse) if node.orelse else None,
                condition_names=_names_in(node.test),
                body_kind=_body_kind(node.body),
            )
        elif isinstance(node, ast.Return):
            self.info.return_lines.add(node.lineno)
        elif isinstance(node, ast.Global):
            self.info.global_names.update(node.names)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                for sub in ast.walk(child):
                    if isinstance(sub, ast.comprehension):
                        self.info.comprehension_names.update(_names_in(sub.target))
        self.scan(node)


class CodeStructure:
    """
    Parses a source string once and answers questions about it by line.

    from_file marks a structure built from a whole module on disk rather
    than a user-supplied snippet, which changes how much source the report
    lists (only the functions that ran, instead of everything).
    """

    def __init__(self, 
                 source: str, 
                 from_file: bool = False) -> None:
        """
        Initialises a CodeStructure instance.

        Args:
            source: The source code to parse.
            from_file: Whether the source is from a file or a snippet.
        """
        
        self.source = source
        self.lines = source.splitlines()
        self.from_file = from_file
        self.functions: list[FunctionInfo] = []
        self._by_key: dict[tuple[str, int], FunctionInfo] = {}
        self._collect(ast.parse(source), prefix="")

    def _collect(self, node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info = self._build_function(child, prefix)
                self.functions.append(info)
                self._by_key[(info.name, info.first_line)] = info
                self._collect(child, prefix=info.qualname + ".")
            elif isinstance(child, ast.ClassDef):
                self._collect(child, prefix=prefix + child.name + ".")
            else:
                self._collect(child, prefix)

    def _build_function(self, node: ast.AST, prefix: str) -> FunctionInfo:
        first_line = node.decorator_list[0].lineno if node.decorator_list else node.lineno
        arguments = node.args
        parameters = [a.arg for a in arguments.posonlyargs + arguments.args + arguments.kwonlyargs]
        if arguments.vararg:
            parameters.append("*" + arguments.vararg.arg)
        if arguments.kwarg:
            parameters.append("**" + arguments.kwarg.arg)
        info = FunctionInfo(
            name=node.name,
            qualname=prefix + node.name,
            first_line=first_line,
            def_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            parameters=parameters,
        )
        _FunctionScanner(info).scan(node)
        return info

    def function_for(self, name: str, first_line: int) -> Optional[FunctionInfo]:
        """Finds the function a code object belongs to, by name and co_firstlineno."""
        return self._by_key.get((name, first_line))

    def line_source(self, line: int) -> str:
        if 1 <= line <= len(self.lines):
            return self.lines[line - 1].strip()
        return ""

    def listing(self, ranges: Optional[list[tuple[int, int]]] = None) -> list[str]:
        """Numbered source lines, either everything or just the given (start, end) ranges."""
        if ranges is None:
            ranges = [(1, len(self.lines))]
        width = len(str(len(self.lines)))
        output: list[str] = []
        previous_end = 0
        for start, end in sorted(ranges):
            start = max(start, previous_end + 1)
            if start > end:
                continue
            if previous_end and start > previous_end + 1:
                output.append(" " * width + " | ...")
            for line in range(start, end + 1):
                output.append(f"{line:>{width}} | {self.lines[line - 1]}")
            previous_end = end
        return output
