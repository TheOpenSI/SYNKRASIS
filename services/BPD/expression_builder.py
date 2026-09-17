import ast
from typing import Union


class ExpressionBuilder:
    """
    Builds a structured, nested representation of an expression tree.

    build() is the single entry point: it dispatches on the node's type,
    and every node type that can contain further expressions recurses back
    through build(), decomposing the whole tree down to names and constants.
    Anything not explicitly handled falls back to an unparsed source string
    rather than raising an error, so unfamiliar code never breaks the walk.
    """

    _BINARY_OPERATORS = {
        ast.Add: "+",
        ast.Sub: "-",
        ast.Mult: "*",
        ast.Div: "/",
        ast.FloorDiv: "//",
        ast.Mod: "%",
        ast.Pow: "**",
        ast.LShift: "<<",
        ast.RShift: ">>",
        ast.BitOr: "|",
        ast.BitXor: "^",
        ast.BitAnd: "&",
        ast.MatMult: "@",
    }

    _COMPARISON_OPERATORS = {
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.Lt: "<",
        ast.LtE: "<=",
        ast.Gt: ">",
        ast.GtE: ">=",
        ast.Is: "is",
        ast.IsNot: "is not",
        ast.In: "in",
        ast.NotIn: "not in",
    }

    _BOOLEAN_OPERATORS = {
        ast.And: "and",
        ast.Or: "or",
    }

    _UNARY_OPERATORS = {
        ast.UAdd: "+",
        ast.USub: "-",
        ast.Not: "not",
        ast.Invert: "~",
    }

    def build(self, node: ast.expr) -> dict:
        if isinstance(node, ast.BinOp):
            return self._build_bin_op(node)
        if isinstance(node, ast.Compare):
            return self._build_compare(node)
        if isinstance(node, ast.BoolOp):
            return self._build_bool_op(node)
        if isinstance(node, ast.UnaryOp):
            return self._build_unary_op(node)
        if isinstance(node, ast.Call):
            return self._build_call(node)
        if isinstance(node, ast.Attribute):
            return self._build_attribute(node)
        if isinstance(node, ast.Name):
            return self._build_name(node)
        if isinstance(node, ast.Constant):
            return self._build_constant(node)
        if isinstance(node, ast.Subscript):
            return self._build_subscript(node)
        if isinstance(node, ast.Tuple):
            return self._build_tuple(node)
        if isinstance(node, ast.Slice):
            return self._build_slice(node)
        return self._build_fallback(node)

    def build_annotation(self, annotation: Union[ast.expr, None]) -> dict:
        """
        Builds a structured entry for a type annotation. Returns an explicit
        "unknown" marker when no annotation was written, rather than trying
        to infer one — inference would need runtime information this parser
        does not have.
        """
        if annotation is None:
            return {"type": "unknown"}
        return self.build(annotation)

    def get_binary_operator_symbol(self, op: ast.AST) -> str:
        """
        Public helper reused by the statement builder for augmented
        assignments (e.g. x += 1), which share BinOp's operator set.
        """
        return self._get_operator_symbol(op, self._BINARY_OPERATORS)

    def _get_operator_symbol(self, op: ast.AST, mapping: dict) -> str:
        return mapping.get(type(op), type(op).__name__)

    def _build_bin_op(self, node: ast.BinOp) -> dict:
        return {
            "type": "binary_operation",
            "lineno": node.lineno,
            "operator": self._get_operator_symbol(node.op, self._BINARY_OPERATORS),
            "left": self.build(node.left),
            "right": self.build(node.right),
        }

    def _build_compare(self, node: ast.Compare) -> dict:
        # ops/comparators are lists to support chains like 0 < x < 10,
        # so this is represented as one left-hand side plus a list of
        # (operator, right-hand side) pairs, rather than a single pair
        comparisons = [
            {
                "operator": self._get_operator_symbol(operator, self._COMPARISON_OPERATORS),
                "right": self.build(comparator),
            }
            for operator, comparator in zip(node.ops, node.comparators)
        ]
        return {
            "type": "comparison",
            "lineno": node.lineno,
            "left": self.build(node.left),
            "comparisons": comparisons,
        }

    def _build_bool_op(self, node: ast.BoolOp) -> dict:
        return {
            "type": "boolean_operation",
            "lineno": node.lineno,
            "operator": self._get_operator_symbol(node.op, self._BOOLEAN_OPERATORS),
            "values": [self.build(value) for value in node.values],
        }

    def _build_unary_op(self, node: ast.UnaryOp) -> dict:
        return {
            "type": "unary_operation",
            "lineno": node.lineno,
            "operator": self._get_operator_symbol(node.op, self._UNARY_OPERATORS),
            "operand": self.build(node.operand),
        }

    def _build_call(self, node: ast.Call) -> dict:
        return {
            "type": "call",
            "lineno": node.lineno,
            "function": self.build(node.func),
            "args": [self.build(arg) for arg in node.args],
            "keywords": [self._build_keyword(keyword) for keyword in node.keywords],
        }

    def _build_keyword(self, node: ast.keyword) -> dict:
        return {
            "name": node.arg,  # None for a **kwargs spread
            "value": self.build(node.value),
        }

    def _build_attribute(self, node: ast.Attribute) -> dict:
        return {
            "type": "attribute",
            "lineno": node.lineno,
            "value": self.build(node.value),
            "attribute_name": node.attr,
        }

    def _build_name(self, node: ast.Name) -> dict:
        return {
            "type": "name",
            "lineno": node.lineno,
            "identifier": node.id,
        }

    def _build_constant(self, node: ast.Constant) -> dict:
        return {
            "type": "constant",
            "lineno": node.lineno,
            "value": node.value,
            "value_type": type(node.value).__name__,
        }

    def _build_subscript(self, node: ast.Subscript) -> dict:
        # covers both real indexing (data[0], my_list[i:j]) and parametrised
        # type hints (list[int], dict[str, int]) — both use this same node
        # type, so "slice" may itself turn out to be a Tuple or a Slice
        # once built, rather than a single plain expression
        return {
            "type": "subscript",
            "lineno": node.lineno,
            "value": self.build(node.value),
            "slice": self.build(node.slice),
        }

    def _build_tuple(self, node: ast.Tuple) -> dict:
        # most relevant here for multi-parameter generics, e.g. the
        # (str, int) pair inside dict[str, int]
        return {
            "type": "tuple",
            "lineno": node.lineno,
            "elements": [self.build(element) for element in node.elts],
        }

    def _build_slice(self, node: ast.Slice) -> dict:
        # a real slice such as my_list[i:j:step] — each part is optional
        return {
            "type": "slice",
            "lineno": node.lineno,
            "lower": self.build(node.lower) if node.lower is not None else None,
            "upper": self.build(node.upper) if node.upper is not None else None,
            "step": self.build(node.step) if node.step is not None else None,
        }

    def _build_fallback(self, node: ast.expr) -> dict:
        # catches expression types not explicitly handled above (Subscript,
        # IfExp, list/dict literals, comprehensions, f-strings, etc.)
        return {
            "type": "unrecognised",
            "lineno": getattr(node, "lineno", None),
            "source": ast.unparse(node),
        }