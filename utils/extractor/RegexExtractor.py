import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import re

class RegexExtractor:
    def __init__(self):
        self.type_cast_function_call = r"[a-z]{,5}\([a-z_]+\([\w,\s]+\)\)" # isTypeCastFunctionCall
        self.extract_type_cast_function_call = r"^[a-z]{,5}\((.*)\)"
        
        self.extract_test_case_function_call = r"(?<=assert\s)(.*?)(?===)"
        
    
    def extract_function_call_from_type_cast(self, function_call: str) -> str:
        """
        Example: int(foo(5)) -> foo(5)
        """
        if re.match(self.type_cast_function_call, function_call):
            return re.search(self.extract_type_cast_function_call, function_call).group(1)
        else:
            return function_call
        
        
    def extract_function_call_from_test_case(self, test_case: str) -> str:
        """
        Example: assert foo(5) == 10 -> foo(5)
        """
        return re.search(self.extract_test_case_function_call, test_case).group()