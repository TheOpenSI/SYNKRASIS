"""
Inject one small bug into a correct solution (mutation testing), so the bug location is known.

    mutants = list_mutants(source)          # [Mutant(source, line, description), ...] in a fixed order
    mutants = list_mutants(source, seed=3)  # another order

Operators: flip a comparison (< <= > >= == !=), swap + and -, change an integer constant by one,
swap and/or, swap min/max, shift a range() bound, swap += and -=. Code is re-printed with ast.unparse
(comments are lost, like in everything else BPD2 shows).
"""
from __future__ import annotations

import ast
import random
from dataclasses import dataclass


@dataclass
class Mutant:
    source: str
    line: int            # line in the ORIGINAL source (after ast.unparse of the original)
    description: str


_COMPARE = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
_BINOP = {ast.Add: ast.Sub, ast.Sub: ast.Add}
_AUG = {ast.Add: ast.Sub, ast.Sub: ast.Add}
_BOOL = {ast.And: ast.Or, ast.Or: ast.And}
_MINMAX = {"min": "max", "max": "min"}


def _sites(tree: ast.AST) -> list[tuple[str, ast.AST]]:
    """Every place a mutation can be applied: (kind, node)."""
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _COMPARE:
            sites.append(("compare", node))
        elif isinstance(node, ast.BinOp) and type(node.op) in _BINOP:
            sites.append(("binop", node))
        elif isinstance(node, ast.AugAssign) and type(node.op) in _AUG:
            sites.append(("augassign", node))
        elif isinstance(node, ast.BoolOp) and type(node.op) in _BOOL:
            sites.append(("boolop", node))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _MINMAX:
            sites.append(("minmax", node))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and node.args:
            sites.append(("range", node))
        elif isinstance(node, ast.Constant) and type(node.value) is int and abs(node.value) <= 10:
            sites.append(("constant", node))
    return sites


def _apply(kind: str, node: ast.AST) -> str:
    if kind == "compare":
        old = type(node.ops[0]); node.ops[0] = _COMPARE[old](); return f"comparison {old.__name__} -> {_COMPARE[old].__name__}"
    if kind == "binop":
        old = type(node.op); node.op = _BINOP[old](); return f"operator {old.__name__} -> {_BINOP[old].__name__}"
    if kind == "augassign":
        old = type(node.op); node.op = _AUG[old](); return f"augmented assignment {old.__name__} -> {_AUG[old].__name__}"
    if kind == "boolop":
        old = type(node.op); node.op = _BOOL[old](); return f"{old.__name__} -> {_BOOL[old].__name__}"
    if kind == "minmax":
        old = node.func.id; node.func.id = _MINMAX[old]; return f"{old} -> {_MINMAX[old]}"
    if kind == "range":
        last = node.args[-1] if len(node.args) < 3 else node.args[1]
        index = len(node.args) - 1 if len(node.args) < 3 else 1
        node.args[index] = ast.BinOp(left=last, op=ast.Sub(), right=ast.Constant(1))
        return "range bound reduced by one"
    node.value = node.value + 1
    return f"constant {node.value - 1} -> {node.value}"


def list_mutants(source: str, seed: int = 0) -> list[Mutant]:
    """All single mutations of source, in a seeded random order."""
    original = ast.unparse(ast.parse(source))
    count = len(_sites(ast.parse(original)))
    order = list(range(count))
    random.Random(seed).shuffle(order)
    mutants = []
    for index in order:
        tree = ast.parse(original)
        kind, node = _sites(tree)[index]
        line = getattr(node, "lineno", 0)
        description = _apply(kind, node)
        mutants.append(Mutant(ast.unparse(ast.fix_missing_locations(tree)), line, description))
    return mutants
