import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import unittest

from utils.code_parsing.parse_codellama import parse_codellama


class TestParseCodellama(unittest.TestCase):

    def test_basic_response(self):
        """
        All sections are separated.
        """
        response = """### Requirements
numpy pandas

### Code
```python
import numpy as np

def calculate_mean(numbers):
    return np.mean(numbers)
```
### Example
```python
numbers = [1, 2, 3, 4, 5]
result = calculate_mean(numbers)
print(f"The mean is: {result}")
```
"""
        expected_code = """import numpy as np

def calculate_mean(numbers):
    return np.mean(numbers)"""
        expected_example = """numbers = [1, 2, 3, 4, 5]
result = calculate_mean(numbers)
print(f"The mean is: {result}")"""

        requirements, code, example = parse_codellama(response)
        self.assertEqual(requirements, ["numpy", "pandas"])
        self.assertEqual(expected_code, code)
        self.assertEqual(expected_example, example)

    def test_code_with_natural_language(self):
        """
        Has natural language, code and example is separated but no title.
        Requirements will be empty list.
        """
        response = """Thank you for bringing this to my attention. I apologize for the oversight in my previous response. The issue is that the `List` type is not defined, as it should be a list of floats. Here is the corrected code with the required imports and definitions:
```
from typing import List
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    for i in range(len(numbers)):
        for j in range(i+1, len(numbers)):
            if abs(numbers[i] - numbers[j]) < threshold:
                return True
    return False
```
And here is the example to run the code:
```
print(has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)) # Output: True
print(has_close_elements([1.0, 2.0, 3.0], 0.5)) # Output: False
```
"""
        expected_code = """from typing import List
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    for i in range(len(numbers)):
        for j in range(i+1, len(numbers)):
            if abs(numbers[i] - numbers[j]) < threshold:
                return True
    return False"""
        expected_example = """print(has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)) # Output: True
print(has_close_elements([1.0, 2.0, 3.0], 0.5)) # Output: False"""

        requirements, code, example = parse_codellama(response)
        self.assertEqual(requirements, [])
        self.assertEqual(expected_code.strip(), code)
        self.assertEqual(expected_example.strip(), example)

    def test_with_no_section(self):
        """
        Has natural language and no section. 
        Example will be empty string.
        Requirements will be empty list.
        """
        response = '''I apologize for the confusion, I will make sure to include the necessary imports in the generated code. Here is the corrected version of the function with the added import statements:
```
from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """

    for i in range(len(numbers) - 1):
        for j in range(i + 1, len(numbers)):
            if abs(numbers[j] - numbers[i]) < threshold:
                return True
    return False
```
'''
        expected_code = '''from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """

    for i in range(len(numbers) - 1):
        for j in range(i + 1, len(numbers)):
            if abs(numbers[j] - numbers[i]) < threshold:
                return True
    return False'''

        requirements, code, example = parse_codellama(response)
        self.assertEqual(requirements, [])
        self.assertEqual(expected_code, code)
        self.assertEqual(example, "")

if __name__ == '__main__':
    unittest.main()