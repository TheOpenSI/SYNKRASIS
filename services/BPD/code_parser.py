import ast

from expression_builder import ExpressionBuilder
from statement_builder import StatementBuilder


class CodeParser:
    """
    Top-level entry point. Parses a source code string into an ordered,
    nested representation of what the code does — statements in sequence,
    with their conditions and values fully decomposed — intended to be
    rendered into a natural-language report for an LLM.
    """

    def __init__(self) -> None:
        self.expression_builder = ExpressionBuilder()
        self.statement_builder = StatementBuilder(self.expression_builder)

    def parse(self, code: str) -> list[dict]:
        module = ast.parse(code)
        return self.statement_builder.build_module(module)
