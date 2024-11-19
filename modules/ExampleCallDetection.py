# =====================================================================================================
# Comments out any example call after function definition
# The current implementation comments out any code that comes after function definition
# Tested with recursive, nested and function with multiple return statements.
# =====================================================================================================

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import re
from typing import List, Tuple


class ExampleCallDetection:
    @staticmethod
    def _get_function_bounds(lines: List[str], function_name: str, start_idx: int) -> Tuple[int, int]:
        """
        Determine the start and end indices of the function in the code.
        Returns (start_line, end_line).
        """
        function_start = -1
        function_end = -1
        base_indent = -1

        # Find function start
        function_def_pattern = rf"def\s+{re.escape(function_name.replace('()', ''))}\s*\(.*\):"

        # Find the function definition
        for i in range(start_idx, len(lines)):
            if re.match(function_def_pattern, lines[i].strip()):
                function_start = i
                base_indent = len(lines[i]) - len(lines[i].lstrip())
                break

        if function_start == -1:
            return -1, -1

        # Find function end
        for i in range(function_start + 1, len(lines)):
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue

            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent:
                function_end = i - 1
                break

        if function_end == -1:
            function_end = len(lines) - 1

        return function_start, function_end


    @staticmethod
    def _find_multiline_return_end(lines: List[str], start_idx: int, base_indent: int) -> int:
        """
        Find the end of a multi-line return statement.
        Returns the index of the last line of the return statement.
        """
        parentheses_count = 0
        current_idx = start_idx

        # Count initial parentheses in the return line
        first_line = lines[start_idx]
        parentheses_count += first_line.count('(') - first_line.count(')')

        # If no parentheses or balanced in first line, return same line
        if parentheses_count == 0:
            return start_idx

        # Look for the closing parenthesis
        while current_idx < len(lines) - 1 and parentheses_count > 0:
            current_idx += 1
            line = lines[current_idx]

            # Skip empty lines
            if not line.strip():
                continue

            # Check if we've gone too far (less indentation than base)
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent:
                break

            parentheses_count += line.count('(') - line.count(')')

        return current_idx


    @staticmethod
    def _find_last_return(lines: List[str], start_idx: int, end_idx: int) -> Tuple[int, int]:
        """
        Find the last return statement and its end line.
        Returns (start_line, end_line) of the return statement.
        """
        last_return_start = -1
        last_return_end = -1
        current_idx = start_idx

        while current_idx <= end_idx:
            line = lines[current_idx].strip()
            if line.startswith('return'):
                base_indent = len(lines[current_idx]) - len(lines[current_idx].lstrip())
                last_return_start = current_idx
                last_return_end = ExampleCallDetection._find_multiline_return_end(
                    lines, current_idx, base_indent
                )
                current_idx = last_return_end + 1
            else:
                current_idx += 1

        return last_return_start, last_return_end


    @staticmethod
    def comment_after_return(content: str, function_name: str) -> str:
        """
        Comments out all lines after the last 'return' statement in the specified function.
        Properly handles multi-line return statements.

        Args:
            content: The content of the Python file as a string.
            function_name: The name of the function to process.
        Returns:
            The modified content with lines after the last return statement commented out.
        """
        lines = content.splitlines()
        modified_lines = []

        # Get function boundaries
        func_start, func_end = ExampleCallDetection._get_function_bounds(lines, function_name, 0)
        if func_start == -1:
            return content

        # Find the last return statement and its end
        last_return_start, last_return_end = ExampleCallDetection._find_last_return(
            lines, func_start, func_end
        )

        # Process lines
        for i, line in enumerate(lines):
            if i <= last_return_end:
                # Lines before or part of the return statement remain unchanged
                modified_lines.append(line)
            elif i <= func_end:
                # Lines after the return statement but within function get commented
                if line.strip():  # Only comment non-empty lines
                    modified_lines.append(f"# {line}")
                else:
                    modified_lines.append(line)
            else:
                # Lines after the function get commented
                if line.strip():
                    modified_lines.append(f"# {line}")
                else:
                    modified_lines.append(line)

        return '\n'.join(modified_lines)