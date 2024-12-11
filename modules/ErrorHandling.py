import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import re
from typing import Union, Tuple
from collections import Counter

from utils.output_message_format.output_colour import print_warning


class ErrorHandling():
    def __init__(self, target_file_name: str = "/usr/src/app/main.py"):
        """
        Error handling Module.
        Target file name is used to extract the file specific error messages.
        """
        self.target_file_name = target_file_name
    
    
    def _unittest_extract_errors(self, error_message: str, total_failed_count: int) -> list[str]:
        """
        Extract all individual test case error messages from a unittest-style error output.
        
        Args:
        - error_message (str): The full error message from the unittest run.
        - total_failed_count (int): The number of failed test cases extracted using the first line.
        
        Returns:
        - error_messages (list): A list of specific error tracebacks for each failed test case.
        """        
        all_error_messages = self._extract_all_tracebacks(error_message)
        
        if total_failed_count != len(all_error_messages):
            print_warning("Error occurred while extracting individual test case error messages, check ErrorHandling module.")
            # raise ValueError("Failed test count does not match the extracted error messages.")
        
        return all_error_messages
    
    
    def _unittest_generate_test_summary(self, test_result_string: str) -> Tuple[dict, str]:
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
        Extract all tracebacks from the error message.
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - list[str]: A list of all tracebacks.
        """
        pattern = (r"((Traceback.*?Error:.*?)(?:\n\s*\n|$)|"
                   r"(Traceback.*?Exception:.*?)(?:\n\s*\n|$))") # To match multithewad error message
        
        all_tracebacks = re.findall(pattern, error_message, re.DOTALL)
        all_tracebacks = [traceback[0] or traceback[1] for traceback in all_tracebacks]

        return all_tracebacks
    
    
    def _get_test_case(self, error_message: str,
                       change_test_case_entry: bool,
                       to_replace: str,
                       entry_point: str) -> str:
        """
        Extract the test case from the error message.
        Call only when error type is AssertionError

        Args:
        - error_message (str): The error message.
        - change_test_case_entry (bool): Change the test case entry. Default is False.
        - to_replace (str): The string to replace. Default is "candidate" for HumanEval.
        - entry_point (str): The entry point.

        Returns:
        - str: The test case.
        """
        if self.get_error_type(error_message) != "AssertionError":
            print_warning("Not an AssertionError")
            return ""

        test_case_pattern = r"(?<=assert)(.*=?)(?=\nAssertionError)"
        test_case = re.search(test_case_pattern, error_message, re.DOTALL).group()
        if test_case:
            if change_test_case_entry:
                test_case = test_case.replace(to_replace, entry_point)

            return test_case
        else:
            print_warning("Test case not found in the error message, SET extract_test_case TO FALSE.")
            return ""
        
        
    def _name_error_line(self, error_message: str) -> str:
        """
        For NAME ERROR only.
        Get the name error line only.

        Args:
        - error_message (str): The error message.

        Returns:
        - str: single error line.
        """
        if self.get_error_type(error_message) != "NameError":
            print_warning("Not an AssertionError")
            return error_message # return the whole error message

        error_message_lines = error_message.split("\n")

        return error_message_lines[-1].strip()


    def get_error_type(self, error_message: str) -> str:
        """
        Get the error type from the error message.\n
        This removes our generic error message from timeout thread first.
        ** Must remove the generic error message if present.

        Args:
        - error_message (str): The error message, can have timeout thread generic error message in it.

        Returns:
        - str: The error type.
        """
        # Remove generic error
        e_m = self.remove_multithread_generic_error(error_message).strip()
        # Extract error type
        error_type = e_m.split("\n")[-1].split(":")[0]

        return error_type.strip()


    def remove_multithread_generic_error(self, error_message: str) -> str:
        """
        Removes the generic error message that is added for experiments.
        Can be used with any error message since it checks the presence of such generic error message internally.

        Logic:
        Look for the traceback block with generic error message and remove it.

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
        if len(all_traceback_blocks) > 1:
            return error_message.replace(all_traceback_blocks[-1], "").strip()
        else:
            print_warning("Regex pattern did not match for removing generic error message.")
            return error_message.strip() # Warning: Had generic error but could not remove


    def remove_external_file_error(self, error_message: str,
                                   target_file_name: str = "/usr/src/app/main.py") -> str:
        """
        Keeps only the error messages related to the target file.\n
        Default target file is /usr/src/app/main.py as in the pycapsule experiments.

        Logic:
        Search the line that contains the target file name, start at that line and keep till the end.

        Args:
        - target_file_name (str): The name of the target file.

        Returns:
        - str: The error message with the external file error message removed.
        """
        target_file_name = target_file_name.replace(".", "\.")
        remove_external_file_pattern = r'File\s"%s.*' % target_file_name
        file_specific_error_message = re.search(remove_external_file_pattern, error_message, re.DOTALL)

        return error_message if file_specific_error_message is None else file_specific_error_message.group().strip()


    def remove_generic_and_external_file_error(self, error_message: str) -> Tuple[str, str]:
        """
        Removes the generic error message and the external file error message.
        This will be the usual ENTRYPOINT.

        Args:
        - error_message (str): The error message.

        Returns:
        - str: Error Type
        - str: Error Message removed of generic and external file error message.
        """
        e_m = self.remove_multithread_generic_error(error_message)
        e_m = self.remove_external_file_error(e_m, self.target_file_name)
        error_type = self.get_error_type(error_message)

        return error_type, e_m


    def assertion_error_prompt(self, error_message: str,
                               extract_test_case: bool,
                               change_test_case_entry: bool,
                               to_replace: str,
                               entry_point: str) -> str:
        """
        Example: Your code failed a test case. Please update the function logic. Error message added for your reference.
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
        _, error_message = self.remove_generic_and_external_file_error(error_message)
        if extract_test_case:
            test_case = self._get_test_case(error_message, change_test_case_entry, to_replace, entry_point).strip()
            return (f"Your generated code failed the following test case - {test_case}.\n"
                    "Please update the function logic so all test cases will pass. "
                    "Error message added for your reference - \n"
                    f"{error_message}")
        else:
            return (f"Your generated code failed a test case.\n"
                    "Please update the function logic so all test cases will pass. "
                    "Error message added for your reference - \n"
                    f"{error_message}")
            
            
    def name_error_prompt(self, error_message: str) -> str:
        """
        Example: Your generated code had a NameError.
        Please check the function, variable names in your generated code and make sure they are same as instruction.
        Error message added for your reference - {error_message}

        Args:
        - error_message (str): The error message.

        Returns:
        - str: The NameError message.
        """
        error_message = self.remove_multithread_generic_error(error_message)
        error_message = self.remove_external_file_error(error_message)
        error_message = self._name_error_line(
            error_message)  # passing only the error line, comment this line to pass the full error message

        return (f"Your generated code had a NameError.\n"
                "Please check the function, variable names in your generated code and "
                "make sure they are same as instruction.\n"
                f"Error message added for your reference - {error_message}")
        
        
    def recursion_error_prompt(self) -> str:
        """
        Example: Your generated code had a RecursionError. 
        Please chnage the function logic to avoid infinite recursion.
        Error message added for your reference - {error_message}
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - str: The RecursionError message.
        """
        # NOTE: May be ideal to pass the actual trimmed error message.
        return ("Your generated code had a RecursionError.\n"
                "Please chnage the function logic to avoid infinite recursion.\n"
                "Error message added for your reference - RecursionError: maximum recursion depth exceeded in comparison")


    def all_other_error_prompt(self, error_message: str, send_original: bool) -> str:
        """
        Example: Your generated code had a/an {error_type}. Please check the error message for more details.
        {error_message}

        Logic:
        - Remove the generic error message.
        - Remove the external file error message.
        - Get the error type.

        Args:
        - error_message (str): The error message.

        Returns:
        - str: The generic error message.
        """
        error_type, error_message_relevant = self.remove_generic_and_external_file_error(error_message)

        if send_original:
            error_message_relevant = error_message

        return (f"Your generated code had a/an {error_type}.\n"
                "Please check the following error message for more details - \n"
                f"{error_message_relevant}")
    
    
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
            processed_error_messages.append(error_message) # NOTE: Can be processed further with e_h(error_message)
            
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
            "Please check the following error messages from the python compiler for your generated solution - \n"
            f"{individual_error_messages}"
        )
        return unittest_error_prompt.strip()


    def __call__(self,
                 error_message: str,
                 send_original: bool = False,  # for generic error prompt
                 extract_test_case: bool = False,  # for assertion error prompt
                 change_test_case_entry: bool = False,  # for assertion error prompt
                 to_replace: str = "candidate",  # for assertion error prompt
                 entry_point: str = None,  # for assertion error prompt, collect from data_point
                 is_unittest: bool = False) -> str:
        """
        Call the respective error prompt function based on the error type.

        Args:
            error_message (str): The error message.

        Returns:
            Query_prompt (str): The error prompt.
        """
        if is_unittest:
            return self.unittest_error_prompt(error_message)
        
        error_type = self.get_error_type(error_message)
        if error_type == "AssertionError":
            return self.assertion_error_prompt(error_message, extract_test_case, change_test_case_entry, to_replace,
                                               entry_point)
        elif error_type == "NameError":
            return self.name_error_prompt(error_message)
        elif error_type == "RecursionError":
            return self.recursion_error_prompt()
        else:
            return self.all_other_error_prompt(error_message, send_original)