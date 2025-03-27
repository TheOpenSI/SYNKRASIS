# =============================================================================
# Error Handling Module.
# Usage - 
#  - get_error_type(error_message: str) -> str
#  - remove_multithread_generic_error(error_message: str) -> str
#  - remove_external_file_error(error_message: str) -> str
#  - remove_generic_and_external_file_error(error_message: str) -> Tuple[str, str]
#  - assertion_error_prompt(error_message: str,
#                           extract_test_case: bool,
#                           change_test_case_entry: bool,
#                           to_replace: str,
#                           entry_point: str) -> str
#  - name_error_prompt(error_message: str) -> str
#  - recursion_error_prompt() -> str
#  - all_other_error_prompt(error_message: str, send_original: bool) -> str
#  - unittest_error_prompt(error_message: str) -> str
#  - is_unittest_error(error_message: str) -> bool
#  - __call__(self,
#             error_message: str,
#             send_original: bool = False,
#             extract_test_case: bool = False,
#             change_test_case_entry: bool = False,
#             to_replace: str = "candidate",
#             entry_point: str = None,
#             is_unittest = False) -> str
# =============================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import re
from typing import Union, Tuple
from collections import Counter

from utils.output_message_format.output_colour import print_warning, print_error


class ErrorHandling():
    def __init__(self, target_file_name: str = "/usr/src/app/main.py"):
        """
        Error handling Module.
        Target file name is used to extract the file specific error messages.
        """
        self.target_file_name = target_file_name
    
    
    def _unittest_extract_errors(self, 
                                 error_message: str, 
                                 total_failed_count: int) -> list[str]:
        """
        Extract all individual test case error message blocks from a 
        unittest-style error output.
        
        Args:
        - error_message (str): The full error message from the unittest run.
        - total_failed_count (int): The number of extracted failed test cases.
        
        Returns:
        - error_messages (list): A list of specific error tracebacks for each 
        failed test case.
        """        
        all_error_messages = self._extract_all_tracebacks(error_message)
        
        if total_failed_count != len(all_error_messages):
            print_warning(("Error occurred while extracting individual test"
                           "case error messages, check ErrorHandling module."))
      
        return all_error_messages
    
    
    def _unittest_generate_test_summary(self, 
                                        test_result_string: str) -> Tuple[dict, str]:
        """
        Given the first line of unittest output, count occurrence and generate summary string.
        . represents a successful test 
        F represents a failed test
        E represents an error
        S represents a skipped test
        x represents an expected failure
        u represents an unexpected success
        
        Args:
            test_result_string (str): The first line of unittest output.
            
        Returns:
            counts (dict): A dictionary of the count of each character in the string.
            Summary message (str): A summary message of the test results.
        """
        char_descriptions = {
            ".": "passed",
            "f": "failed",
            "e": "resulted error in",
            "s": "skipped",
            "x": "expected failure in",
            "u": "got unexpected success in"
        }
        
        # Count occurrences of each character
        counts = Counter(test_result_string.lower())
        
        # Generate summary messages
        summary_messages = []
        for char, count in counts.items():
            description = char_descriptions.get(char, f"got {char} in")
            case_or_cases = "case" if count == 1 else "cases"
            message = f"Your solution {description} {count} test {case_or_cases}."
            summary_messages.append(message)
        
        # Join messages if there are multiple
        return counts, "\n".join(summary_messages)
    
    
    def _extract_all_tracebacks(self, error_message: str) -> list[str]:
        """
        Extract all traceback blocks from the error message.
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - list[str]: A list of all tracebacks.
        """
        # Check the expected block count.
        expected_block_count = error_message.count("Traceback")
        
        pattern = re.compile(
            r"""(Traceback[\s\S]*?"""
            r"""(?:[A-Za-z\.]+[Ee]rror(?::\s*.*?)?|Exception(?::\s*.*?)?)"""
            r"""(?=\s*Traceback|\n\s*\n|\n\s*$|$))""", 
            re.VERBOSE | re.DOTALL
        )
        all_tracebacks = re.findall(pattern, error_message)
        
        if len(all_tracebacks) != expected_block_count:
            print_error((f"Expected traceback block count does not match actual count for - \n"
                         f"{error_message}"))
            raise ValueError("Expected traceback block count does not match actual count")

        return all_tracebacks
        
    
    def _get_test_case(self, error_message: str,
                       change_test_case_entry: bool,
                       to_replace: str,
                       entry_point: str) -> str:
        """
        Extract the test case from the AssertionError message.

        Args:
        - error_message (str): The error message.
        - change_test_case_entry (bool): Change the test case entry. Default is False.
        - to_replace (str): The string to replace. Default is "candidate" for HumanEval.
        - entry_point (str): The entry point.

        Returns:
        - str: The test case.
        """
        if self.get_error_type(error_message) != "AssertionError":
            print_warning("Not an AssertionError.")
            return ""

        test_case_pattern = r"(?<=assert)(.*=?)(?=\nAssertionError)"
        test_case = re.search(test_case_pattern, error_message, re.DOTALL).group()
        if test_case:
            # For HumanEval: Candidate.
            if change_test_case_entry:
                test_case = test_case.replace(to_replace, entry_point)
            return test_case.strip()
        else:
            print_warning(("Test case not found in the error message, "
                          "SET extract_test_case TO FALSE."))
            return "" # NOTE: This can be changed to return the assertion error line.
        
        
    def _name_error_line(self, error_message: str) -> str:
        """
        Get the last name error line only.

        Args:
        - error_message (str): The error message.

        Returns:
        - str: single error line.
        """
        if self.get_error_type(error_message) != "NameError":
            print_warning("Not a NameError, failure detected at __call__.")
            return error_message # return the whole error message

        error_message_lines = error_message.split("\n")
        # Will not work if the error message is not in the last line.
        return error_message_lines[-1].strip()


    def get_error_type(self, error_message: str) -> str:
        """
        Get the error type from the error message.\n
        Removes the timesafe generic error message from timeout thread first.

        Args:
        - error_message (str): The error message, can have timeout thread generic 
            error message in it.

        Returns:
        - str: The error type.
        """
        # Remove generic error
        e_m = self.remove_multithread_generic_error(error_message).strip()
        
        # Infinite loop issue
        if "Generated code is running infinite loop" in e_m:
            return "Infinite Loop"
        
        # Extract error type
        error_message_list = e_m.split("\n")
        error_message_list.reverse() # In place reverse.
        for error_message_line in error_message_list:
            if re.match(r"^[A-Za-z\.]+[Ee]rror.*", error_message_line):
                return error_message_line.split(":")[0].strip()
        
        print_warning(f"Error type not found in error message:\n{error_message}")
        raise ValueError("Error type not found in error message")


    def remove_multithread_generic_error(self, error_message: str) -> str:
        """
        Removes the generic error message that is added for pycapsule experiments.

        Args:
        - error_message (str): The error message.

        Returns:
        - str: The error message with the generic error message removed.
        """
        # Return the error message if generic error message is not present
        if "This is a generic error message." not in error_message:
            return error_message.strip()
        
        # Detect all traceback blocks
        all_traceback_blocks = self._extract_all_tracebacks(error_message)
        
        if len(all_traceback_blocks) == 0:
            print_error("Extracting traceback blocks failed.")
            raise ValueError("Extracting traceback blocks failed.")

        elif len(all_traceback_blocks) == 1:
            # Warning: Had generic error but could not remove it.
            print_error(("Generic error message is present but could not remove it, "
                         "extracting all blocks failed."))
            raise ValueError(("Generic error message is present but could not remove it, "
                         "extracting all blocks failed."))
        
        else:
            # The last traceback block is the generic error message.
            return error_message.replace(all_traceback_blocks[-1], "").strip()
            

    def remove_external_file_error(self, error_message: str) -> str:
        """
        Keeps only the error messages related to the target file.

        Args:
        - error_message (str): The error message.

        Returns:
        - str: The error message with the external file error message removed.
        """
        target_file_name = re.escape(self.target_file_name)
        target_file_pattern = r'File\s"%s.*' % target_file_name
        file_specific_error_message = re.search(target_file_pattern, 
                                                error_message, 
                                                re.DOTALL)

        return (
            error_message 
            if file_specific_error_message is None 
            else file_specific_error_message.group().strip()
        )


    def remove_generic_and_external_file_error(self, 
                                               error_message: str) -> Tuple[str, str]:
        """
        Removes the generic error message and the external file error message.

        Args:
        - error_message (str): The error message.

        Returns:
        - str: Error type.
        - str: Error message without generic and external file error message.
        """
        e_m = self.remove_multithread_generic_error(error_message)
        e_m = self.remove_external_file_error(e_m)
        error_type = self.get_error_type(error_message)

        return error_type, e_m


    def assertion_error_prompt(self, error_message: str,
                               extract_test_case: bool,
                               change_test_case_entry: bool,
                               to_replace: str,
                               entry_point: str) -> str:
        """
        Example: Your code failed a test case. Please update the function logic. 
        Error message added for your reference.
        {error_message}

        or,
        Your code failed the following test case - {test_case}.
        Please update the function logic. Error message added for your reference.
        {error_message}

        Args:
        - error_message (str): The error message.
        - entry_point (str): The entry point.
        - extract_test_case (bool): Extract the test case. Default is False.
        - change_test_case_entry (bool): Change the test case entry. Default is False.
        - to_replace (str): The string to replace. Default is "candidate" for HumanEval.
        - entry_point (str): The actual entry point or function name.

        Returns:
        - str: The assertion error message.
        """
        if extract_test_case:
            test_case = self._get_test_case(error_message, 
                                            change_test_case_entry, 
                                            to_replace, 
                                            entry_point).strip()
            return (f"Your generated code failed the following test case - {test_case}.\n"
                    "Please update the function logic so all test cases will pass. "
                    "Error message added for your reference - \n"
                    f"{error_message}")
        else:
            return (f"Your generated code failed a test case.\n"
                    "Please update the function logic so all test cases will pass. "
                    "Error message added for your reference - \n"
                    f"{error_message}")
            
            
    def is_unittest_error(self, error_message: str) -> bool:
        """
        Determine if the output originated from unittest (True) 
        or a simple function with assertions (False).
        
        Args:
            error_message (str): The output from test execution
            
        Returns:
            bool: True if unittest output, False if function output
        """
        # Clean the message and handle empty input
        if not error_message or not error_message.strip():
            return False  # Empty output typically comes from simple functions
        
        # Split into lines for analysis
        lines = error_message.strip().splitlines()
        
        # Unittest specific patterns
        unittest_patterns = [
            # Successful tests
            r"^Ran\s+\d+\s+tests?\s+in\s+[\d\.]+s$",       # "Ran X tests in Y.ZZZs"
            r"^OK$",                                        # "OK" on its own line
            # Failed tests
            r"^FAILED\s+\((?:\w+=\d+,?\s*)+\)$",           # "FAILED (failures=1, errors=2)"
            r"^FAIL:\s+test_\w+\s+\(\w+(\.\w+)*\)$",       # "FAIL: test_name (TestClass.test_name)"
            r"^ERROR:\s+test_\w+\s+\(\w+(\.\w+)*\)$",      # "ERROR: test_name (TestClass.test_name)"
        ]
        
        # Check each line against patterns
        for line in lines:
            for pattern in unittest_patterns:
                if re.match(pattern, line):
                    return True
        
        # Special check for the last line which is often a summary in unittest
        last_line = lines[-1] if lines else ""
        
        # Last line unittest check (strong indicator)
        if (re.match(r"^OK$", last_line) or 
            re.match(r"^FAILED\s+\((?:\w+=\d+,?\s*)+\)$", last_line)):
            return True
        
        # If no unittest patterns found, assume it's a function test
        return False
            
            
    def name_error_prompt(self, error_message: str) -> str:
        """
        Example: Your generated code had a NameError.
        Please check the function, variable names in your generated code and 
        make sure they are same as instruction.
        Error message added for your reference - {error_message}

        Args:
        - error_message (str): The error message.

        Returns:
        - str: The NameError message.
        """
        # passing only the error line, comment the next line to pass the full error message
        error_message = self._name_error_line(error_message)  

        return (f"Your generated code had a NameError.\n"
                "Please check the function, variable names in your generated code and "
                "make sure they are same as instruction.\n"
                f"Error message added for your reference - {error_message}")
        
        
    def recursion_error_prompt(self) -> str:
        """
        RecursionError prompt.
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - str: The RecursionError message.
        """
        return ("Your generated code had a RecursionError.\n"
                "Please chnage the function logic to avoid infinite recursion.\n"
                "Error message added for your reference - "
                "RecursionError: maximum recursion depth exceeded in comparison")


    def all_other_error_prompt(self, error_message: str) -> str:
        """
        Example Output: 
        Your generated code had a/an {_extract_all_tracebackserror_type}. 
        Please check the error message for more details.
        {error_message}

        Args:
        - error_message (str): The error message.

        Returns:
        - str: The generic error message.
        """
        error_type = self.get_error_type(error_message)

        return (f"Your generated code had a/an {error_type}.\n"
                "Please check the following error message for more details - \n"
                f"{error_message}")
    
    
    def unittest_error_prompt(self, error_message: str) -> str:
        """
        Handle the error message from a unittest-style error output.

        Args:
            error_message (str): _description_

        Returns:
            str: _description_
        """
        target = self.remove_multithread_generic_error(error_message)
        
        # First line for summary
        first_line = target.split("\n")[0]
        
        # Summary prompt
        count_dict, summary_result = self._unittest_generate_test_summary(first_line)
        
        # Number of expected error messages
        # NOTE: This is not the actual error count, but the number of failed test cases
        # NOTE: Need to check how expected fail x and unexpected success u are handled
        error_count = sum(value for key, value in count_dict.items() if key != ".")
        
        # Extract individual error messages
        error_messages = self._unittest_extract_errors(target, error_count)
        
        # Keeping the uniqe error messages only
        error_messages = list(set(error_messages))
        
        # Process all individual error messages
        processed_error_messages = []
        for i, error_message in enumerate(error_messages):
            processed_error_messages.append("-"*50)
            processed_error_messages.append(f"Error {i + 1}:")
            processed_error_messages.append(f"Error type: {self.get_error_type(error_message)}")
            # NOTE: Can be processed further with e_h(error_message)
            processed_error_messages.append(error_message)
            
        # Individual error messages
        # individual_error_messages = "\n".join(processed_error_messages)
        individual_error_messages = "\n".join(processed_error_messages[:4]) + "-"*50
        
        # unittest_error_prompt = (
        #     f"Your generated code had issues in {error_count} test cases.\n"
        #     "### SUMMARY:\n"
        #     f"{summary_result}\n"
        #     "Please check the following error messages for more details - \n"
        #     f"{individual_error_messages}"
        # )
        unittest_error_prompt = (
            "Please check the following error messages from the python compiler "
            "for your generated solution - \n"
            f"{individual_error_messages}"
        )
        return unittest_error_prompt.strip()


    def __call__(self,
                 error_message: str,
                 send_original: bool = False,  # for generic error prompt
                 extract_test_case: bool = False,  # for assertion error prompt
                 change_test_case_entry: bool = False,  # for assertion error prompt
                 to_replace: str = "candidate",  # for assertion error prompt
                 entry_point: str = None) -> str:
        """
        Call the respective error prompt function based on the error type.

        Args:
            error_message (str): The error message.
            send_original (bool): Send the original error message. 
                Default is False, used in all_other_error_prompt.
            extract_test_case (bool): Extract the test case. 
                Default is False, used for assertion_error_prompt only.
            change_test_case_entry (bool): Change the test case entry. 
                Default is False, used for assertion_error_prompt only.
            to_replace (str): The string to replace. 
                Default is "candidate", used for assertion_error_prompt only.
            entry_point (str): The entry point. 
                Default is None, used for assertion_error_prompt only.

        Returns:
            Query_prompt (str): The error prompt.
        """
        # Process Process - n: issue
        error_message = re.sub(r"Process Process-[\d]+:", "", error_message).strip()
        # Unit test error
        if self.is_unittest_error(error_message):
            return self.unittest_error_prompt(error_message)
        
        error_type, error_message_concise = self.remove_generic_and_external_file_error(error_message)
        
        if error_type == "AssertionError":
            return self.assertion_error_prompt(error_message_concise, 
                                               extract_test_case, 
                                               change_test_case_entry, 
                                               to_replace, 
                                               entry_point)
        
        elif error_type == "NameError":
            return self.name_error_prompt(error_message_concise)
        
        elif error_type == "RecursionError":
            return self.recursion_error_prompt()
        
        else:
            return (error_message
                    if send_original
                    else self.all_other_error_prompt(error_message_concise))