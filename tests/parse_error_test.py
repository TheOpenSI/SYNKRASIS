import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import unittest
from utils.error_parsing.parse_error import parse_error

# ==================================================================
class response:
    def __init__(self, stderr: str):
        self.stderr = stderr
# ==================================================================

class TestExtractError(unittest.TestCase):

    def test_assertion_error(self):
        error_message = """
WARNING: You are using pip version 21.1.1; however, version 21.2.4 is available.
Traceback (most recent call last):
    File "/usr/src/app/main.py", line 22, in <module>
    check(generate_integers)
    File "/usr/src/app/main.py", line 12, in check
    assert candidate(2, 10) == [2, 4, 6, 8], 'Test 1'
AssertionError: Test 1
        """
        resp = response(error_message)
        data_point = {"entry_point": "generate_integers"}
        expected_output = "The following test case 'Test 1' failed and resulted in AssertionError.\nError message: generate_integers(2, 10) == [2, 4, 6, 8], 'Test 1'"
        self.assertEqual(parse_error(resp, data_point), expected_output)

    def test_syntax_error(self):
        error_message = """
Traceback (most recent call last):
    File "<string>", line 1, in <module>
    print "unknown OS, please update setup.py"
        ^
SyntaxError: Missing parentheses in call to 'print'. Did you mean print("unknown OS, please update setup.py")?
        """
        resp = response(error_message)
        data_point = {"entry_point": "generate_integers"}
        expected_output = "A SyntaxError occurred.\nError message: " + error_message
        self.assertEqual(parse_error(resp, data_point), expected_output)

    def test_multiple_errors(self): # assertion error is given priority
        error_message = """
Traceback (most recent call last):
    File "<string>", line 1, in <module>
    print "unknown OS, please update setup.py"
        ^
SyntaxError: Missing parentheses in call to 'print'. Did you mean print("unknown OS, please update setup.py")?
----------------------------------------
ERROR: Command errored out with exit status 1: python setup.py egg_info Check the logs for full command output.
Traceback (most recent call last):
    File "/usr/src/app/main.py", line 22, in <module>
    check(generate_integers)
    File "/usr/src/app/main.py", line 12, in check
    assert candidate(2, 10) == [2, 4, 6, 8], 'Test 1'
AssertionError: Test 1
        """
        resp = response(error_message)
        data_point = {"entry_point": "generate_integers"}
        expected_output = "The following test case 'Test 1' failed and resulted in AssertionError.\nError message: generate_integers(2, 10) == [2, 4, 6, 8], 'Test 1'"
        self.assertEqual(parse_error(resp, data_point), expected_output)

    def test_no_error(self):
        error_message = ""
        resp = response(error_message)
        data_point = {"entry_point": "generate_integers"}
        expected_output = ""
        self.assertEqual(parse_error(resp, data_point), expected_output)

if __name__ == '__main__':
    unittest.main()