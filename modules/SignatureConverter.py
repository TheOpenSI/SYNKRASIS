import re
import keyword
from collections import defaultdict
from typing import Any, List, Tuple


class SignatureConverter:
    @staticmethod
    def sanitise_variable_name(name):
        """
        Fixes a string to make it a valid Python variable name.
        
        Parameters:
        - name (str): The input string to sanitize.

        Returns:
        - str: A valid Python variable name.
        """
        # Replace invalid characters with underscores
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        
        # Ensure the name doesn't start with a digit
        if name and name[0].isdigit():
            name = f"_{name}"
        
        # Ensure the name isn't a Python reserved keyword
        if keyword.iskeyword(name):
            name = f"{name}_var"
        
        return name

    
    
    @staticmethod
    def parse_function_call(call_string: str) -> Tuple[str, List[str]]:
        """
        Parse a function call string to extract the function name and arguments as strings.
        
        Args:
            call_string (str): The function call string, e.g., "foo(1, 2)".
        
        Returns:
            Tuple[str, List[str]]: The function name and a list of argument strings.
        """
        # Regex pattern to match the function name and arguments
        pattern = r"(\w+)\s*\((.*)\)"
        match = re.match(pattern, call_string)
        
        if not match:
            raise ValueError("Invalid function call string")
        
        func_name = match.group(1)  # The function name
        args_string = match.group(2)  # The arguments as a single string
        
        # Split the arguments, handling nested structures like lists or custom objects
        arguments = []
        current_arg = ''
        depth = 0  # Tracks nesting level (e.g., for parentheses)
        
        for char in args_string:
            if char in '([{':  # Increase depth for opening brackets
                depth += 1
            elif char in ')]}':  # Decrease depth for closing brackets
                depth -= 1
            elif char == ',' and depth == 0:  # Argument separator at top level
                arguments.append(current_arg.strip())
                current_arg = ''
                continue
            current_arg += char
        
        if current_arg:  # Add the last argument
            arguments.append(current_arg.strip())
        
        return func_name, arguments


    @staticmethod
    def evaluate_argument(arg: str) -> Any:
        """
        Evaluate an argument and determine its type or structure.
        
        Args:
            arg (str): The argument string, e.g., "1", "Root(5)".
        
        Returns:
            Any: The evaluated argument or its string representation.
        """
        try:
            # Evaluate the argument to determine its type
            return eval(arg)
        except NameError:
            # If eval raises a NameError, it's likely a custom class or undefined variable
            match = re.match(r"(\w+)\((.*)\)", arg)
            if match:
                # Custom class instantiation, e.g., Root(5)
                return f"{match.group(1)} instance"
            return f"custom_class_{arg}"  # Unknown argument type
        except Exception:
            # Catch other exceptions and return the raw string
            return arg


    @staticmethod
    def get_type_name(arg: Any) -> str:
        """
        Determine the type of an argument.
        
        Args:
            arg (Any): The argument, which may be a literal, list, or custom class.
        
        Returns:
            str: The type name, e.g., "int", "Root".
        """
        if isinstance(arg, list):  # Handle lists
            if arg:
                element_type = SignatureConverter.get_type_name(arg[0])
                return f"List[{element_type}]"
            return "List"
        elif isinstance(arg, str) and arg.endswith("instance"):  # Handle custom classes
            return arg.split()[0]  # Extract the class name
        elif isinstance(arg, str) and arg.startswith("custom_class_"):  # Handle unknown classes
            temp: str = arg.replace("custom_class_", "")
            return temp[0].upper() + temp[1:]
        return type(arg).__name__  # Fallback to built-in types


    @staticmethod
    def convert(call_string: str) -> str:
        """
        Convert a function call string into its signature with argument types.
        
        Args:
            call_string (str): The function call string, e.g., "foo(1, 2)".
        
        Returns:
            str: The formatted function signature, e.g., "foo(arg_int: int, arg_2: int)".
        """
        func_name, args = SignatureConverter.parse_function_call(call_string)
        
        # Track argument counts by type to ensure unique parameter names
        type_counts = defaultdict(int)  # Using defaultdict directly
        
        params = []
        for arg in args:
            # Evaluate the argument to determine its value or structure
            evaluated_arg = SignatureConverter.evaluate_argument(arg)
            # Determine the type name
            type_name = SignatureConverter.get_type_name(evaluated_arg)
            
            # Generate a parameter name based on its type
            base_name = f"arg_{type_name.lower()}"
            base_name = SignatureConverter.sanitise_variable_name(base_name)
            
            type_counts[base_name] += 1
            
            # Add a numeric suffix for duplicate types
            if type_counts[base_name] > 1:
                param_name = f"{base_name}_{type_counts[base_name]}"
            else:
                param_name = base_name
            
            # Format the parameter with its type
            params.append(f"{param_name}: {type_name}")
        
        # Combine the function name and parameters into a signature
        return f"{func_name}({', '.join(params)})"