import ast
from typing import Union
from expression_builder import ExpressionBuilder


class StatementBuilder:
    """
    Builds an ordered, nested representation of a sequence of statements.

    Depends on an ExpressionBuilder to decompose any condition or value
    encountered along the way. A function definition is built the same way
    whether it appears at module level or nested inside another function —
    the nesting itself is already visible from where the entry sits within
    its parent's "body" list, so no separate "nested" type is needed.
    """

    def __init__(self, expression_builder: ExpressionBuilder) -> None:
        self.expression_builder = expression_builder

    def build_module(self, module: ast.Module) -> list[dict]:
        return self.build_body(module.body)

    def build_body(self, statements: list[ast.stmt]) -> list[dict]:
        return [self.build_statement(statement) for statement in statements]

    def build_statement(self, node: ast.stmt) -> dict:
        if isinstance(node, ast.If):
            return self._build_if(node)
        if isinstance(node, ast.For):
            return self._build_for(node)
        if isinstance(node, ast.While):
            return self._build_while(node)
        if isinstance(node, ast.Try):
            return self._build_try(node)
        if isinstance(node, ast.Return):
            return self._build_return(node)
        if isinstance(node, ast.AnnAssign):
            return self._build_ann_assign(node)
        if isinstance(node, ast.Assign):
            return self._build_assign(node)
        if isinstance(node, ast.AugAssign):
            return self._build_aug_assign(node)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return self._build_import(node)
        if isinstance(node, ast.ClassDef):
            return self._build_class_definition(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return self._build_function_definition(node)
        if isinstance(node, (ast.Break, ast.Continue, ast.Pass)):
            return self._build_simple_keyword_statement(node)
        if isinstance(node, ast.Expr):
            return self._build_expr_statement(node)
        return self._build_statement_fallback(node)

    def _build_if(self, node: ast.If) -> dict:
        # an "elif" is not a distinct node type — it appears as another If
        # sitting inside orelse, so it is handled automatically by the
        # recursive call to build_body below, with no special-casing needed
        return {
            "type": "if",
            "lineno": node.lineno,
            "condition": self.expression_builder.build(node.test),
            "body": self.build_body(node.body),
            "orelse": self.build_body(node.orelse),
        }

    def _build_for(self, node: ast.For) -> dict:
        return {
            "type": "for",
            "lineno": node.lineno,
            "target": self.expression_builder.build(node.target),
            "iterable": self.expression_builder.build(node.iter),
            "body": self.build_body(node.body),
            "orelse": self.build_body(node.orelse),
        }

    def _build_while(self, node: ast.While) -> dict:
        return {
            "type": "while",
            "lineno": node.lineno,
            "condition": self.expression_builder.build(node.test),
            "body": self.build_body(node.body),
            "orelse": self.build_body(node.orelse),
        }

    def _build_try(self, node: ast.Try) -> dict:
        return {
            "type": "try",
            "lineno": node.lineno,
            "body": self.build_body(node.body),
            "handlers": [self._build_except_handler(handler) for handler in node.handlers],
            "orelse": self.build_body(node.orelse),
            "finalbody": self.build_body(node.finalbody),
        }

    def _build_except_handler(self, node: ast.ExceptHandler) -> dict:
        exception_type = node.type
        return {
            "type": "except",
            "lineno": node.lineno,
            "exception_type": self.expression_builder.build(exception_type)
            if exception_type is not None
            else None,
            "name": node.name,
            "body": self.build_body(node.body),
        }

    def _build_return(self, node: ast.Return) -> dict:
        return {
            "type": "return",
            "lineno": node.lineno,
            "value": self.expression_builder.build(node.value) if node.value is not None else None,
        }

    def _build_ann_assign(self, node: ast.AnnAssign) -> dict:
        return {
            "type": "annotated_assignment",
            "lineno": node.lineno,
            "target": self.expression_builder.build(node.target),
            "annotation": self.expression_builder.build_annotation(node.annotation),
            "value": self.expression_builder.build(node.value) if node.value is not None else None,
        }

    def _build_assign(self, node: ast.Assign) -> dict:
        # a plain assignment carries no annotation in the AST at all, so the
        # data type is genuinely unknown from static parsing alone
        return {
            "type": "assignment",
            "lineno": node.lineno,
            "targets": [self.expression_builder.build(target) for target in node.targets],
            "annotation": self.expression_builder.build_annotation(None),
            "value": self.expression_builder.build(node.value),
        }

    def _build_aug_assign(self, node: ast.AugAssign) -> dict:
        return {
            "type": "augmented_assignment",
            "lineno": node.lineno,
            "target": self.expression_builder.build(node.target),
            "operator": self.expression_builder.get_binary_operator_symbol(node.op),
            "value": self.expression_builder.build(node.value),
        }

    def _build_import(self, node: Union[ast.Import, ast.ImportFrom]) -> dict:
        return {
            "type": "import",
            "lineno": node.lineno,
            "module": getattr(node, "module", None),  # only ImportFrom has this
            "names": [alias.name for alias in node.names],
        }

    def _build_class_definition(self, node: ast.ClassDef) -> dict:
        return {
            "type": "class_definition",
            "lineno": node.lineno,
            "name": node.name,
            "bases": [self.expression_builder.build(base) for base in node.bases],
            "body": self.build_body(node.body),
        }

    def _build_function_definition(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> dict:
        return {
            "type": "function_definition",
            "lineno": node.lineno,
            "name": node.name,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "parameters": self._build_parameters(node.args),
            "return_annotation": self.expression_builder.build_annotation(node.returns),
            "body": self.build_body(node.body),
        }

    def _build_parameters(self, args: ast.arguments) -> list[dict]:
        return [
            {
                "name": argument.arg,
                "annotation": self.expression_builder.build_annotation(argument.annotation),
            }
            for argument in args.args
        ]

    def _build_simple_keyword_statement(self, node: Union[ast.Break, ast.Continue, ast.Pass]) -> dict:
        return {
            "type": type(node).__name__.lower(),  # "break", "continue", or "pass"
            "lineno": node.lineno,
        }

    def _build_expr_statement(self, node: ast.Expr) -> dict:
        # a bare expression used as a statement — most commonly a call whose
        # return value is discarded, or a standalone docstring
        return {
            "type": "expression_statement",
            "lineno": node.lineno,
            "value": self.expression_builder.build(node.value),
        }

    def _build_statement_fallback(self, node: ast.stmt) -> dict:
        # catches statement types not explicitly handled above (With,
        # Delete, Raise, Assert, match statements, etc.)
        return {
            "type": "unrecognised_statement",
            "lineno": getattr(node, "lineno", None),
            "source": ast.unparse(node),
        }
