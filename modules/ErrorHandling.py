# =======================================================================================================
# Error Handling Module
# Usage:
#   remove_multithread_generic_error(error_message: str): removes the generic error message.
# =======================================================================================================

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import re
from typing import Tuple
from collections import Counter

from utils.output_message_format.output_colour import print_warning, print_error


class ErrorHandling():
    def __init__(self, target_file_name: str = "/usr/src/app/main.py"):
        """
        Error handling Module.
        Target file name is used to extract the file specific error messages.
        """
        self.target_file_name = target_file_name


    @staticmethod
    def is_unittest_error(error_message: str) -> bool:
        """
        Check if the error message is a unittest error.
        Checks if the last line matched FAILED(fail_type=number,?\s?)

        Args:
            error_message (str): The error message.

        Returns:
            is_unittest_flag (bool): True if the error message is a unittest error.

        Raises:
            ValueError: Must remove the generic error message
        """
        # Unittest pattern
        unittest_pattern: str = r"FAILED\s{1}\((?:\w+\=\d+,?\s?)+\)"

        # Edge case and generic error message
        if "This is a generic error message" in error_message:
            print_error("Must remove the generic error message.")
            raise ValueError("Must remove the generic error message.")

        # Get the last line
        last_line: str = error_message.strip().splitlines()[-1]

        # Check if the last line matches the unittest pattern
        return re.match(unittest_pattern, last_line) is not None


    @staticmethod
    def remove_multithread_generic_error(error_message: str) -> str:
        """
        Removes the generic error message that is added for pycapsule experiments.
        Checks presence of generic message internally.

        Args:
        - error_message (str): The error message.

        Returns:
        - generic_error_removed_error_message (str):
        Error message with the generic error message removed.
        """
        # Return the error message if generic error message is not present
        if "This is a generic error message." not in error_message:
            return error_message.strip()

        # Generic Error message
        pattern = (r'Traceback \(most recent call last\):\n\s*'
                   r'File "/usr/src/app/main.py", line \d+, in <module>\n\s*'
                   r'raise Exception\(\'An error occurred. This is a generic error message. '
                   r'See previous error message\'\).*')

        return re.sub(pattern, "", error_message, flags=re.DOTALL|re.MULTILINE).strip()


    def remove_external_file_error(self, error_message: str) -> str:
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
        target_file_name = self.target_file_name.replace(".", "\.") # Escape the dot
        remove_external_file_pattern = r'File\s"%s.*' % target_file_name
        file_specific_error_message = re.search(remove_external_file_pattern, error_message, re.DOTALL)

        return error_message if file_specific_error_message is None \
            else file_specific_error_message.group().strip()


    def get_error_type(self, error_message: str) -> str:
        """
        Get the error type from the error message.

        Args:
        - error_message (str): The error message, can have timeout thread generic error message in it.

        Returns:
        - error_type (str): The error type.
        """
        # Remove generic error
        e_m = self.remove_multithread_generic_error(error_message)

        # Extract error type
        error_type = e_m.split("\n")[-1].split(":")[0]

        if re.match(r"[A-Z][a-z]+[Ee]rror", error_type.strip()) is None:
            print_warning("Error type does not match the expected pattern.")

        return error_type.strip()


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
        e_m = self.remove_external_file_error(e_m)
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
        _, error_message = self.remove_generic_and_external_file_error(error_message)
        # passing only the error line, comment the next line to pass the full error message
        error_message = self._name_error_line(error_message)

        return (f"Your generated code had a NameError.\n"
                "Please check the function, variable names in your generated code and "
                "make sure they are same as instruction.\n"
                f"Error message added for your reference - {error_message}")


    def recursion_error_prompt(self) -> str:
        """
        Example: Your generated code had a RecursionError.
        Please change the function logic to avoid infinite recursion.
        Error message added for your reference -
        RecursionError: maximum recursion depth exceeded in comparison

        Args:
        - error_message (str): The error message.

        Returns:
        - str: The RecursionError message.
        """
        # NOTE: May be ideal to pass the actual error message's trimmed version.
        target_file_name = self.target_file_name  # Just to remove pycharm warning
        return ("Your generated code had a RecursionError.\n"
                "Please change the function logic to avoid infinite recursion.\n"
                "Error message added for your reference - "
                "RecursionError: maximum recursion depth exceeded in comparison")


    def unittest_error_prompt(self, error_message: str) -> str:
        """
        Example:
        Please check the following error messages from the python compiler for your generated solution -

        Args:
            error_message (str): Unit test error message.

        Returns:
            str: Single error message, sends the first one.
        """
        target = self.remove_multithread_generic_error(error_message)

        # First line for summary
        first_line = target.split("\n")[0]
        # Check if the first line matches the unittest pattern, raise warning if not
        if re.match(r"[FfEeSsXxUu.]+", first_line) is None:
            print_warning("First line does not match the expected pattern.")

        # Extract individual error messages
        extracted_error_messages = self._unittest_extract_errors(target)

        # Keeping the unique error messages only
        extracted_error_messages = list(set(extracted_error_messages))
        if len(extracted_error_messages) <= 0:
            print_error("Traceback extract failed. No error messages found.")
            return error_message

        # Sending single error message
        unittest_error_prompt = (
            "Please check the following error messages from the python compiler "
            "for your generated solution - \n"
            f"{extracted_error_messages[0]}"
        )
        return unittest_error_prompt.strip()


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


    def _unittest_extract_all_tracebacks(self, error_message: str) -> list[str]:
        """
        Extract all tracebacks from the error message.

        Args:
        - error_message (str): The error message.

        Returns:
        - list[str]: A list of all tracebacks.
        """
        target_file_name = self.target_file_name  # Just to remove pycharm warning
        pattern = r"(Traceback.*?[Ee]rror:.*?)(?:\n\s*\n|$)"  # To match multithread error message

        all_tracebacks = re.findall(pattern, error_message, re.DOTALL)
        return all_tracebacks


    def _unittest_extract_errors(self, error_message: str) -> list[str]:
        """
        Extract all individual test case error message blocks from a unittest-style error output.

        Args:
        - error_message (str): The full error message from the unittest run.

        Returns:
        - error_messages (list): A list of specific error tracebacks for each failed test case.
        """
        error_message =  self.remove_multithread_generic_error(error_message)
        all_error_messages = self._unittest_extract_all_tracebacks(error_message)

        expected_block_count = error_message.count("Traceback")
        if expected_block_count != len(all_error_messages):
            print_warning(f"'Traceback count: {expected_block_count}', "
                          f"Traceback block count : {len(all_error_messages)}")

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
        target_file_name = self.target_file_name # Just to remove pycharm warning
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
            print_warning("Not a NameError")
            return error_message  # return the whole error message

        error_message_lines = error_message.split("\n")

        return error_message_lines[-1].strip()


    def __call__(self,
                 error_message: str,
                 send_original: bool = False,  # for generic error prompt
                 extract_test_case: bool = False,  # for assertion error prompt
                 change_test_case_entry: bool = False,  # for assertion error prompt
                 to_replace: str = "candidate",  # for assertion error prompt
                 entry_point: str = None,  # for assertion error prompt, collect from data_point
                 ) -> str:
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
        error_message = self.remove_multithread_generic_error(error_message)

        if self.is_unittest_error(error_message):
            return self.unittest_error_prompt(error_message)

        # Non unittest errors
        error_type = self.get_error_type(error_message)

        if error_type == "AssertionError":
            return self.assertion_error_prompt(error_message,
                                               extract_test_case,
                                               change_test_case_entry,
                                               to_replace,
                                               entry_point)

        elif error_type == "NameError":
            return self.name_error_prompt(error_message)

        elif error_type == "RecursionError":
            return self.recursion_error_prompt()

        else:
            return self.all_other_error_prompt(error_message, send_original)