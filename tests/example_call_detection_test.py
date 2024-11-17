import os, sys, unittest
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

from modules.ExampleCallDetection import Example_call_detection

# ============== Example 1 ==============
example_1 = """
def foo(a: int, b: int) -> int:
    return a + b
#===========
print(foo(1, 2))
"""

# ============== Example 2 ==============
example_2 = """
def foo(a: int, b: int) -> int:
    return a + b
#===========
result = foo(1, 2)
print(result)
"""
# ============== Example 3 ==============
example_3 = """
def foo_helper(a: int, b: int) -> int:
    return a + b
def foo(a: int, b: int) -> int:
    return foo_helper(a, b)
#===========
result = foo(1, 2)
print(result)
"""
example_1 = example_1.strip()
example_2 = example_2.strip()
example_3 = example_3.strip()
# =======================================

class TestExampleCallDetection(unittest.TestCase):
    def test_detect_function_name(self):
        call_detection = Example_call_detection(example_1)
        lines, function_name, def_line_num = call_detection.detect_function_name()
        self.assertEqual(function_name, "foo")
        self.assertEqual(def_line_num, 0)

        call_detection = Example_call_detection(example_2)
        lines, function_name, def_line_num = call_detection.detect_function_name()
        self.assertEqual(function_name, "foo")
        self.assertEqual(def_line_num, 0)

        call_detection = Example_call_detection(example_3)
        lines, function_name, def_line_num = call_detection.detect_function_name()
        self.assertEqual(function_name, "foo_helper")
        self.assertEqual(def_line_num, 0)


    def test_detect_function_details(self):
        call_detection = Example_call_detection(example_1)
        lines, function_name, def_line_num = call_detection._detect_given_function_details("foo()")
        self.assertEqual(function_name, "foo()")
        self.assertEqual(def_line_num, 0)

        call_detection = Example_call_detection(example_2)
        lines, function_name, def_line_num = call_detection._detect_given_function_details("foo()")
        self.assertEqual(function_name, "foo()")
        self.assertEqual(def_line_num, 0)

        call_detection = Example_call_detection(example_3)
        lines, function_name, def_line_num = call_detection._detect_given_function_details("foo()")
        self.assertEqual(function_name, "foo()")
        self.assertEqual(def_line_num, 2) # given_function_name
        
        call_detection = Example_call_detection(example_3)
        lines, function_name, def_line_num = call_detection._detect_given_function_details("foo_helper()")
        self.assertEqual(function_name, "foo_helper()")
        self.assertEqual(def_line_num, 0)
        
        
    def test_comment_out_example_calls(self):
        keyword = "#==========="
        # Test case 1: Simple function with direct print call
        call_detection = Example_call_detection(example_1)
        commented_code = call_detection.comment_out_example_calls(is_full_file=False,
                                                                  key_word=keyword,
                                                                  given_function_name="foo()")
        expected_output = """
def foo(a: int, b: int) -> int:
    return a + b
#===========
# print(foo(1, 2))"""
        self.assertEqual(commented_code.strip(), expected_output.strip())

        # Test case 2: Function with assignment and print
        call_detection = Example_call_detection(example_2)
        commented_code = call_detection.comment_out_example_calls(is_full_file=False,
                                                                  key_word=keyword,
                                                                  given_function_name="foo()")
        expected_output = """
def foo(a: int, b: int) -> int:
    return a + b
#===========
# result = foo(1, 2)
# print(result)
"""
        self.assertEqual(commented_code.strip(), expected_output.strip())


        # Test case 3: Multiple functions with example calls
        call_detection = Example_call_detection(example_3)
        commented_code = call_detection.comment_out_example_calls(is_full_file=False,
                                                                  key_word=keyword,
                                                                  given_function_name="foo()")
        expected_output = """
def foo_helper(a: int, b: int) -> int:
    return a + b
def foo(a: int, b: int) -> int:
    return foo_helper(a, b)
#===========
# result = foo(1, 2)
# print(result)
"""
        self.assertEqual(commented_code.strip(), expected_output.strip())
        
        
        # Test case 4: Multiple functions with example calls
        call_detection = Example_call_detection(example_3)
        commented_code = call_detection.comment_out_example_calls(is_full_file=False,
                                                                  key_word=keyword,
                                                                  given_function_name="foo_helper()")
        # No example call, will simply return the original code
        expected_output = """
def foo_helper(a: int, b: int) -> int:
    return a + b
def foo(a: int, b: int) -> int:
    return foo_helper(a, b)
#===========
result = foo(1, 2)
print(result)
"""
        self.assertEqual(commented_code.strip(), expected_output.strip())
        
        # Test case 5: Multiple functions with example calls
        call_detection = Example_call_detection(example_3)
        commented_code = call_detection.comment_out_example_calls(is_full_file=False,
                                                                  key_word=keyword,
                                                                  given_function_name=None)
        # No example call, will simply return the original code
        expected_output = """
def foo_helper(a: int, b: int) -> int:
    return a + b
def foo(a: int, b: int) -> int:
    return foo_helper(a, b)
#===========
result = foo(1, 2)
print(result)
"""
        self.assertEqual(commented_code.strip(), expected_output.strip())
        
        # full file test
        example_test = """
def foo_helper():
    pass
    
def foo():
    pass
    
foo_helper()
foo()
print(foo())

#===========
def test_setup():
    foo_helper()
    foo()
    print(foo())
    
def time_out_func():
    foo_helper()
    foo()
    print(foo())
"""
        call_detection = Example_call_detection(example_test)
        commented_code = call_detection.comment_out_example_calls(is_full_file=True,
                                                                  key_word=keyword,
                                                                  given_function_name="foo()")
        expected_output = """
def foo_helper():
    pass
    
def foo():
    pass
    
foo_helper()
# foo()
# print(foo())


def test_setup():
    foo_helper()
    foo()
    print(foo())
    
def time_out_func():
    foo_helper()
    foo()
    print(foo())
"""     
        self.assertEqual(commented_code.strip(), expected_output.strip())

if __name__ == '__main__':
    unittest.main()