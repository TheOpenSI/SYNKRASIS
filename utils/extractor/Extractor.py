import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import ast

class Extractor:
    @staticmethod
    def remove_leading_bracket(function_call: str) -> str:
        """
        Check if function call is surrounded by brackets and remove the outer brackets.

        Args:
            function_call (str): The function call.

        Returns:
            str: The function call without the leading bracket.
        """
        if function_call.startswith("("):
            function_call = function_call.strip()
            return function_call[1:-1]
        else:
            return function_call
        
        
    @staticmethod
    def get_function_name_from_call(function_call: str) -> str:
        """
        Get the function name from the function call.

        Args:
            function_call (str): The function call.

        Returns:
            str: The function name.
        """
        tree = ast.parse(function_call)
        function_name = tree.body[0].value.func.id
        
        return function_name.strip()