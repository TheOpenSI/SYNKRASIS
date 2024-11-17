import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import re
from typing import Union, Tuple, List

from utils.output_message_format.output_colour import print_warning, print_info, print_success

class Example_call_detection():
    def __init__(self, file_content:str) -> None:
        self.file_content = file_content
    
    
    def detect_function_name(self) -> Union[Tuple[List[str], str, int], Tuple[None, None, None]]:
        """
        Find the first function definition in py content.
        This will detect inner functions as well, so it's necessary that we break after the first function definition.

        Returns:
            Union[Tuple[str, int], None]: Tuple containing function name and line number if found, else None
        """
        lines = [line.strip() for line in self.file_content.split("\n")]
        
        function_name = None
        def_line_num = None

        for i, line in enumerate(lines):
            # Look for function definition
            if line.startswith("def "): # Strip will remove all leading tabs
                # Extract function name using regex
                match = re.match(r"def\s+([a-zA-Z_][a-zA-Z0-9_]+)\s*\(", line)
                if match:
                    function_name = match.group(1)
                    def_line_num = i
                    break
                    
        return (lines, function_name, def_line_num) if function_name else (None, None, None)
    
    
    def _detect_given_function_details(self, function_name: str) -> Union[Tuple[List[str], str, int], 
                                                                          Tuple[None, str, None]]:
        """
        Detects where function_name is defined in the file_content.\n
        Use as alternative to detect_function_name() if you already know the function name.
        
        Args:
            function_name (str): Function name to search for.

        Returns:
            Union[Tuple[str, int], None]: Tuple with function name and line no if found, or (None, function_name, None)
        """
        lines = [line.strip() for line in self.file_content.split("\n")]
        
        def_line_num = None

        for i, line in enumerate(lines):
            # Look for function definition
            if line.startswith("def "): # Strip will remove all leading tabs
                if function_name.strip()[:-1] in line:
                    def_line_num = i
                    break
                    
        return (lines, function_name, def_line_num) if def_line_num is not None else (None, function_name, None)
    
    
    def detect_example_calls(self, given_function_name: str = None) -> List[int]:
        """
        Detect if a function is called after its definition in a Python file.
        If given_function_name is None, the first function definition will be used using detect_function_name().
        
        Args:
            given_function_name (str): Function name to search for. If None, the first function definition will be used.

        Returns:
            List[int]: List of line numbers where the function is called
        """
        example_calls: List[int] = []
        # Find the first function definition
        if given_function_name:
            lines, function_name, def_line_num = self._detect_given_function_details(given_function_name)
            function_name = function_name.replace("()", "").strip() # Patch to support the original logic
        else:
            lines, function_name, def_line_num = self.detect_function_name()

        if not def_line_num:
            print_warning("No function definition found in solution.")
            return example_calls
               
        example_call_pattern = rf"\b{re.escape(function_name)}\s*\("
        for i, line in enumerate(lines[def_line_num + 1:]):
            # Skip comments
            if not line or line.strip().startswith("#"):
                continue

            # Function Definition or Return Statement for recursive functions
            if line.startswith("def ") or ("return" in line):
                continue

            # Check if function is called
            if re.search(example_call_pattern, line):
                example_calls.append(i + def_line_num)

        return example_calls
    
    
    def comment_out_example_calls(self, 
                                  is_full_file: bool = False, 
                                  key_word: str = None, 
                                  given_function_name: str = None) -> str:
        """
        Comment out example calls in the Python file content.
        
        Args:
            is_full_file (bool): If True, will split by keyword first to separate the solution from the setup.
            key_word (str): Keyword to separate the solution from the setup. Default is None.
            given_function_name (str): Function name to search for. If None, the first function definition will be used.

        Returns:
            str: Python file content with example calls commented out
        """
        if is_full_file:
            # File content has solution and test cases
            # Separate solution from test cases
            # Solution is before the key_word
            llm_solution = self.file_content.split(key_word)[0].strip()
            # Test cases
            setup = self.file_content.split(key_word)[1].strip()
            # Content to comment out
            self.file_content = llm_solution
        
        example_calls = self.detect_example_calls(given_function_name=given_function_name)

        if len(example_calls) == 0:
            print_info("No example calls found in the solution. Solution safe to use.")
            return self.file_content + "\n\n\n" + setup if is_full_file else self.file_content
        
        lines = self.file_content.split("\n")
        for i in range(example_calls[0], len(lines)-1):
            lines[i+1] = "# " + lines[i+1]

        target = "\n".join(lines) + "\n\n\n" + setup if is_full_file else "\n".join(lines)
        return target
    