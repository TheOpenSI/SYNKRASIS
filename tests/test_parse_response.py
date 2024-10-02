import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import unittest
from typing import List, Tuple
from utils.code_parsing.code_parser import parse_response

class TestParseResponse(unittest.TestCase):
    
    def test_case_1(self):
        response = '''
### Step-by-step reasoning
Some reasoning steps.

### Requirements
None

### Code
```
print("Hello, World!")
```
'''
        expected_requirements = []
        expected_code = 'print("Hello, World!")'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_2(self):
        response = '''
### Step-by-step reasoning
More reasoning.

### Requirements
numpy, pandas

### Code
```python
import numpy as np
import pandas as pd
```
'''
        expected_requirements = ['numpy', 'pandas']
        expected_code = 'import numpy as np\nimport pandas as pd'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_3(self):
        response = '''
### Step-by-step reasoning
Another example.

### Requirements
None

### Code
```python
def greet(name):
    print(f"Hello, {name}")
```
'''
        expected_requirements = []
        expected_code = 'def greet(name):\n    print(f"Hello, {name}")'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_4(self):
        response = '''
### Step-by-step reasoning
Reasoning text.

### Requirements
requests

### Code
```
import requests

def fetch_data(url):
    return requests.get(url)
```
'''
        expected_requirements = ['requests']
        expected_code = 'import requests\n\ndef fetch_data(url):\n    return requests.get(url)'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_5(self):
        response = '''
### Step-by-step reasoning
Reasoning steps.

### Requirements
None

### Code
```
def example():
    pass
```
'''
        expected_requirements = []
        expected_code = 'def example():\n    pass'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_6(self):
        response = '''
### Step-by-step reasoning
Step-by-step process.

### Requirements
numpy, scipy

### Code
```python
import numpy as np
import scipy as sp
```
'''
        expected_requirements = ['numpy', 'scipy']
        expected_code = 'import numpy as np\nimport scipy as sp'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_7(self):
        response = '''
### Step-by-step reasoning
Explanation of process.

### Requirements
None

### Code
```python
def process_data(data):
    return data * 2
```
'''
        expected_requirements = []
        expected_code = 'def process_data(data):\n    return data * 2'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_8(self):
        response = '''
### Step-by-step reasoning
More steps here.

### Requirements
pandas

### Code
```
import pandas as pd
```
'''
        expected_requirements = ['pandas']
        expected_code = 'import pandas as pd'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_9(self):
        response = '''
### Step-by-step reasoning
Describing the steps.

### Requirements
torch, transformers

### Code
```python
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
```
'''
        expected_requirements = ['torch', 'transformers']
        expected_code = 'import torch\nfrom transformers import GPT2LMHeadModel, GPT2Tokenizer'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

    def test_case_10(self):
        response = '''
### Step-by-step reasoning
Some process explanation.

### Requirements
None

### Code
```
def add(a, b):
    return a + b
```
        '''
        expected_requirements = []
        expected_code = 'def add(a, b):\n    return a + b'
        self.assertEqual(parse_response(response), (expected_requirements, expected_code))

if __name__ == "__main__":
    unittest.main()
