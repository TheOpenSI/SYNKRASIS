import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import unittest

from modules.ErrorHandling import ErrorHandling

class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.maxDiff = 2048
        self.e_h = ErrorHandling("/usr/src/app/main.py")
        
        self.indentation_error = """Traceback (most recent call last):
  File "/usr/lib/python3.8/multiprocessing/process.py", line 315, in _bootstrap
    self.run()
  File "/usr/lib/python3.8/multiprocessing/process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
  File "/usr/src/app/main.py", line 59, in test_execution
    exec(code, test_env)
  File "<string>", line 6
    def separate_duration(df):
    ^
IndentationError: expected an indented block
Traceback (most recent call last):
  File "/usr/src/app/main.py", line 81, in <module>
    raise Exception('An error occurred. This is a generic error message. See previous error message')
Exception: An error occurred. This is a generic error message. See previous error message
"""

        self.assertion_error = """Traceback (most recent call last):
  File "/usr/lib/python3.8/multiprocessing/process.py", line 315, in _bootstrap
    self.run()
  File "/usr/lib/python3.8/multiprocessing/process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
  File "/usr/src/app/main.py", line 10, in test_function
    assert similar_elements((3, 4, 5, 6),(5, 7, 4, 10)) == (4, 5)
AssertionError
Traceback (most recent call last):
  File "/usr/src/app/main.py", line 23, in <module>
    raise Exception('An error occurred. This is a generic error message. See previous error message')
Exception: An error occurred. This is a generic error message. See previous error message
"""
        self.name_error = """Traceback (most recent call last):
  File "/usr/lib/python3.8/multiprocessing/process.py", line 315, in _bootstrap
    self.run()
  File "/usr/lib/python3.8/multiprocessing/process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
  File "/usr/src/app/main.py", line 13, in test_function
    assert maximum_Sum([[1,2,3],[4,5,6],[10,11,12],[7,8,9]]) == 33
NameError: name 'maximum_Sum' is not defined
Traceback (most recent call last):
  File "/usr/src/app/main.py", line 26, in <module>
    raise Exception('An error occurred. This is a generic error message. See previous error message')
Exception: An error occurred. This is a generic error message. See previous error message
"""

        self.module_not_found_error = """Traceback (most recent call last):
  File "/usr/src/app/main.py", line 4, in <module>
    import sympy
ModuleNotFoundError: No module named 'sympy'
"""

        self.syntax_error = """File "/usr/src/app/main.py", line 17
    result.extend([count, lst[-1])
                                 ^
SyntaxError: closing parenthesis ')' does not match opening parenthesis '['
"""


    # Type test
    def test_type(self):
        self.assertEqual("AssertionError", self.e_h.get_error_type(self.assertion_error))
        self.assertEqual("IndentationError", self.e_h.get_error_type(self.indentation_error))
        self.assertEqual("ModuleNotFoundError", self.e_h.get_error_type(self.module_not_found_error))
        self.assertEqual("NameError", self.e_h.get_error_type(self.name_error))
        self.assertEqual("SyntaxError", self.e_h.get_error_type(self.syntax_error))
        
        
    def test_assertion(self):
        expected = ("Your generated code failed the following test case - similar_elements((3, 4, 5, 6),(5, 7, 4, 10)) == (4, 5).\n"
                    "Please update the function logic so all test cases will pass. Error message added for your reference - \n"
                    'File "/usr/src/app/main.py", line 10, in test_function\n'
                    "    assert similar_elements((3, 4, 5, 6),(5, 7, 4, 10)) == (4, 5)\n"
                    "AssertionError")
        self.assertEqual(expected, self.e_h.assertion_error_prompt(self.assertion_error, extract_test_case=True))
        
        
    def test_name_error(self):
        # Checking just the single line
        # Tests the remove_generic_and_external_file_error method as well
        expected = "NameError: name 'maximum_Sum' is not defined"
        _, name_error_line_only = self.e_h.remove_generic_and_external_file_error(self.name_error)
        self.assertEqual(expected, self.e_h._name_error_line(name_error_line_only))
        
        expected = ("Your generated code had a NameError.\n"
                    "Please check the function, variable names in your generated code and make sure they are same as instruction.\n"
                    "Error message added for your reference - NameError: name 'maximum_Sum' is not defined")
        self.assertEqual(expected, self.e_h.name_error_prompt(self.name_error)) 
        
        
    def test_generic_error(self):        
        indentation_expected = ("Your generated code had a/an IndentationError.\n"
                                "Please check the following error message for more details - \n"
                                'File "/usr/src/app/main.py", line 59, in test_execution\n'
                                "    exec(code, test_env)\n"
                                '  File "<string>", line 6\n'
                                "    def separate_duration(df):\n"
                                "    ^\n"
                                "IndentationError: expected an indented block")
        
        module_not_found_expected = ("Your generated code had a/an ModuleNotFoundError.\n"
                                     "Please check the following error message for more details - \n"
                                     'File "/usr/src/app/main.py", line 4, in <module>\n'
                                     "    import sympy\n"
                                     "ModuleNotFoundError: No module named 'sympy'")
        
        syntax_expected = ("Your generated code had a/an SyntaxError.\n"
                            "Please check the following error message for more details - \n"
                            'File "/usr/src/app/main.py", line 17\n'
                            "    result.extend([count, lst[-1])\n"
                            "                                 ^\n"
                            "SyntaxError: closing parenthesis ')' does not match opening parenthesis '['")
        
        
        self.assertEqual(indentation_expected, self.e_h.generic_error_prompt(self.indentation_error))
        self.assertEqual(module_not_found_expected, self.e_h.generic_error_prompt(self.module_not_found_error))
        self.assertEqual(syntax_expected, self.e_h.generic_error_prompt(self.syntax_error))
        
if __name__ == '__main__':
    unittest.main()