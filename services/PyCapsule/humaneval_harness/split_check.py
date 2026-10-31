# =============================================================================================
# HumanEval has one function check(candidate) with many asserts. split_check turns the test code of a task into
# a unittest TestCase with one test per assert, so the BigCodeBench harness can run and report the tests one by one.
#
#   def check(candidate):                       class TestCases(unittest.TestCase):
#       import math                                 def test_1(self):
#       assert candidate(1) == 2                        candidate = <entry_point>
#       assert candidate(2) == 3                        import math
#       for x in range(3):                              _result = candidate(1)
#           assert candidate(x) == x + 1                assert _result == 2, "candidate(1) returned " + repr(_result)
#                                                   def test_2(self): ...
#
# - Every top level assert of check is a test, a loop or a with block of check is one test.
# - The other statements before a test (imports, variables) run in front of every test that follows them.
# - A failed comparison says what the function returned, e.g. "AssertionError: candidate([1, 2], 0.3) returned False".
# - Everything outside check (helper functions, constants) stays at the top of the module.
# =============================================================================================

import ast

_OPERATORS = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
              ast.Is: "is", ast.IsNot: "is not", ast.In: "in", ast.NotIn: "not in"}


def _with_message(node: ast.Assert) -> list[ast.stmt]:
    """
    assert a == b  ->  _result = a
                       assert _result == b, "a returned " + repr(_result)
    Only a comparison without a message. The failed assertion then says what the function returned.
    """
    test = node.test
    if node.msg is not None or not isinstance(test, ast.Compare) or len(test.ops) != 1 or type(test.ops[0]) not in _OPERATORS:
        return [node]
    message = ast.BinOp(left = ast.Constant(f"{ast.unparse(test.left)} returned "), op = ast.Add(),
                        right = ast.parse("repr(_result)", mode = "eval").body)
    check = ast.Assert(test = ast.Compare(left = ast.Name("_result", ast.Load()), ops = test.ops,
                                          comparators = test.comparators), msg = message)
    return [ast.Assign(targets = [ast.Name("_result", ast.Store())], value = test.left, lineno = 0), check]


def split_check(test_code: str, entry_point: str) -> str:
    module = ast.parse(test_code)
    check = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "check")
    outside = [node for node in module.body if node is not check]

    tests, setup = [], []                       # setup: the statements in front of the next test
    for statement in check.body:
        if isinstance(statement, ast.Assert):
            tests.append(setup + _with_message(statement))
        elif any(isinstance(child, ast.Assert) for child in ast.walk(statement)):
            tests.append(setup + [statement])
        else:
            setup = setup + [statement]
    if not tests:                               # nothing to assert: the whole check is one test
        tests.append(check.body)

    methods = []
    for number, statements in enumerate(tests, 1):
        body = [ast.parse(f"candidate = {entry_point}").body[0]] + statements
        methods.append(ast.FunctionDef(name = f"test_{number:03d}", args = ast.parse("def f(self): pass").body[0].args,
                                       body = body, decorator_list = [], returns = None, type_params = []))
    test_case = ast.ClassDef(name = "TestCases", bases = [ast.parse("unittest.TestCase", mode = "eval").body],
                             keywords = [], body = methods, decorator_list = [], type_params = [])
    imports = ast.parse("import unittest").body
    result = ast.Module(body = imports + outside + [test_case], type_ignores = [])
    return ast.unparse(ast.fix_missing_locations(result))
