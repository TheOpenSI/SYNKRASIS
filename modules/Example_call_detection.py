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
    
    
    def detect_example_calls(self) -> List[int]:
        """
        Detect if a function is called after its definition in a Python file.

        Returns:
            tuple: (function_name, bool indicating if example call exists, line number of call if found)
        """
        example_calls: List[int] = []
        # Find the first function definition
        lines, function_name, def_line_num = self.detect_function_name()

        if not function_name:
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
    
    
    def comment_out_example_calls(self, is_full_file: bool = False, key_word: str = "") -> str:
        """
        Comment out example calls in the Python file content.

        Returns:
            str: Python file content with example calls commented out
        """
        if is_full_file:
            llm_solution = self.file_content.split(key_word)[0].strip()
            setup = self.file_content.split(key_word)[1].strip()
            self.file_content = llm_solution
        
        example_calls = self.detect_example_calls()

        if len(example_calls) == 0:
            print_info("No example calls found in the solution. Solution safe to use.")
            return self.file_content + "\n\n\n" + setup if is_full_file else self.file_content
        
        lines = self.file_content.split("\n")
        for i in range(example_calls[0], len(lines)-1):
            lines[i+1] = "# " + lines[i+1]

        target = "\n".join(lines) + "\n\n\n" + setup if is_full_file else "\n".join(lines)
        return target
    
    
# if __name__ == "__main__":
#     example_solution = """
# import heapq

# def find_minimum_range(arrays):
#     def find_minimum_range(arrays):
#         pass
    
#     min_heap = []
#     max_value = float('-inf')
    
#     # Initialize the heap with the first element of each array and track the maximum value
#     for i, arr in enumerate(arrays):
#         heapq.heappush(min_heap, (arr[0], i))
#         max_value = max(max_value, arr[0])
    
#     min_range = float('inf')
#     range_start = 0
    
#     while True:
#         # Extract the smallest element from the heap
#         current_min, array_index = heapq.heappop(min_heap)
        
#         # Calculate the current range
#         if max_value - current_min < min_range:
#             min_range = max_value - current_min
#             range_start = current_min
        
#         # If any array is exhausted, break the loop
#         if len(arrays[array_index]) == 1:
#             break
        
#         # Otherwise, insert the next element from the same array
#         next_element = arrays[array_index][1]
#         heapq.heappush(min_heap, (next_element, array_index))
        
#         # Update the maximum value if necessary
#         max_value = max(max_value, next_element)
    
#     return (range_start, range_start + min_range) + find_minimum_range([[3, 6, 8, 10, 15], [1, 5, 12], [4, 8, 15, 16], [2, 6]])

# # Example function call
# find_minimum_range([[3, 6, 8, 10, 15], [1, 5, 12], [4, 8, 15, 16], [2, 6]])
# result = 2

# # =================== Test Function ===================
# def test_function():
#     pass
# """
#     keyword = "# =================== Test Function ==================="
#     call_detector = Example_call_detection(example_solution)
#     print(call_detector.comment_out_example_calls(is_full_file=True, key_word = keyword))
    