import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import ast
from typing import Tuple, List, Any
from collections import defaultdict

class SignatureConverter:
    @staticmethod
    def parse_function_call(call_string: str) -> Tuple[str, List[Any]]:
        """Parse a function call string into function name and arguments."""
        try:
            tree = ast.parse(call_string)
            call = tree.body[0].value
            
            func_name = call.func.id
            args = []
            for arg in call.args:
                if isinstance(arg, ast.List):
                    args.append([ast.literal_eval(elt) for elt in arg.elts])
                else:
                    args.append(ast.literal_eval(arg))
                    
            return func_name, args
        except Exception as e:
            raise ValueError(f"Invalid function call string: {e}")

    @staticmethod
    def get_type_name(value: Any) -> str:
        """Get the type name for a value."""
        if isinstance(value, list):
            if value:
                element_type = SignatureConverter.get_type_name(value[0])
                return f"List[{element_type}]"
            return "List"
        return type(value).__name__

    @staticmethod
    def convert(call_string: str) -> str:
        """Convert a function call string to its type signature."""
        func_name, args = SignatureConverter.parse_function_call(call_string)
        
        # Keep track of type counts
        type_counts = defaultdict(int)
        
        # Generate parameter names and their types
        params = []
        for arg in args:
            type_name = SignatureConverter.get_type_name(arg)
            base_name = f"arg_{type_name.lower().split('[')[0]}"
            
            # Increment count for this type
            type_counts[base_name] += 1
            
            # Add counter suffix if there's more than one of this type
            if type_counts[base_name] > 1:
                param_name = f"{base_name}_{type_counts[base_name]}"
            else:
                param_name = base_name
            
            params.append(f"{param_name}: {type_name}")
            
        return f"{func_name}({', '.join(params)})"