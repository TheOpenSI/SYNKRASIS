import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import re
from typing import Union, Tuple

from utils.output_message_format.output_colour import print_warning

class ErrorHandling():
    def __init__(self, target_file_name: str = "/usr/src/app/main.py"):
        self.target_file_name = target_file_name
    
    
    @staticmethod
    def get_error_type(error_message: str) -> str:
        """
        Get the error type from the error message.\n
        ** Must remove the experiemental error message if present.
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - str: The error type.
        """
        e_m = ErrorHandling.remove_multithred_generic_error(error_message).strip()
        error_type = e_m.split("\n")[-1].split(":")[0]
        
        return error_type.strip()

    
    
    @staticmethod
    def remove_multithred_generic_error(error_message: str) -> str:
        """
        Removes the generic error message that is added to for experiments.
        
        Logic:
        Using re to remove the last Traceback block.
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - str: The error message with the generic error message removed.
        """
        if "This is a generic error message." not in error_message:
            return error_message.strip()
        
        multi_thread_pattern = r"Traceback(.*)(?=Traceback)"
        removed_generic_error_message = re.search(multi_thread_pattern, error_message, re.DOTALL)
        if removed_generic_error_message is not None:
            error_message = removed_generic_error_message.group()
            return error_message.strip()
        else:
            print_warning("Regex pattern did not match for removing generic error message.")
            return error_message.strip()
        
        
    @staticmethod
    def remove_external_file_error(error_message: str, target_file_name: str = "/usr/src/app/main.py") -> str:
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
        file_specific_error_message = re.search(remove_external_file_pattern, error_message, re.DOTALL).group()
        
        return file_specific_error_message.strip()
    
    
    def remove_generic_and_external_file_error(self, error_message: str) -> Tuple[str, str]:
        """
        Removes the generic error message and the external file error message.
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - str: Error Type
        - str: Error Message removed of generic and external file error message.
        """
        e_m = self.remove_multithred_generic_error(error_message)
        e_m = self.remove_external_file_error(e_m, self.target_file_name)
        error_type = self.get_error_type(error_message)
        
        return error_type, e_m
    
    
    def _get_test_case(self, error_message: str, 
                       change_test_case_entry: bool, 
                       to_replace:str, 
                       entry_point:str) -> str:
        """
        Extract the test case from the error message.
        
        Args:
        - error_message (str): The error message.
        - change_test_case_entry (bool): Change the test case entry. Default is False.
        - to_replace (str): The string to replace. Default is "candidate" for HumanEval.
        - entry_point (str): The entry point.
        
        Returns:
        - str: The test case.
        """
        test_case_pattern = r"(?<=assert)(.*=?)(?=\nAssertionError)"
        test_case = re.search(test_case_pattern, error_message, re.DOTALL).group()
        if test_case:
            if change_test_case_entry:
                test_case = test_case.replace(to_replace, entry_point)
            
            return test_case
        else:
            print_warning("Test case not found in the error message.")
            return ""

        
    
    
    def assertion_error_prompt(self, error_message: str,  
                               extract_test_case: bool, 
                               change_test_case_entry: bool,
                               to_replace: str,
                               entry_point: str) -> str:
        """
        Example: Your code failed a test case. Please update the function logic. Error message added for your reference.
        {error_message}
        
        or,
        Your code failed the following test case - {test_case}. Please update the function logic. Error message added for your reference.
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
                    "Please update the function logic so all test cases will pass. Error message added for your reference - \n"
                    f"{error_message}")
        else:
            return (f"Your generated code failed a test case.\n"
                    "Please update the function logic so all test cases will pass. Error message added for your reference - \n"
                    f"{error_message}")
            
            
    def _name_error_line(self, error_message: str) -> str:
        """
        For NAME ERROR only.
        Get the name error line only.
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - str: single error line.
        """
        error_message_lines = error_message.split("\n")
        
        return error_message_lines[-1].strip()
            
            
    def name_error_prompt(self, error_message: str) -> str:
        """
        Example: Your generated code had a NameError. 
        Please check the function, varibale names in your generated code and make sure they are same as instruction.
        Error message added for your reference - {error_message}
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - str: The NameError message.
        """
        error_message = self.remove_multithred_generic_error(error_message)
        error_message = self.remove_external_file_error(error_message)
        error_message = self._name_error_line(error_message) # passing only the error line, comment this line to pass the full error message
        
        return (f"Your generated code had a NameError.\n"
                "Please check the function, variable names in your generated code and make sure they are same as instruction.\n"
                f"Error message added for your reference - {error_message}")
    
    
    def generic_error_prompt(self, error_message: str, send_original: bool) -> str:
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
        
        
    def __call__(self, 
                 error_message: str, 
                 send_original: bool = False, # for generic error prompt
                 extract_test_case: bool = False, # for assertion error prompt 
                 change_test_case_entry: bool = False, # for assertion error prompt
                 to_replace: str = "candidate", # for assertion error prompt
                 entry_point: str = None # for assertion error prompt, collect from data_point
                 ) -> str:
        """
        Call the respective error prompt based on the error type.
        
        Args:
        - error_message (str): The error message.
        
        Returns:
        - str: The error prompt.
        """
        error_type = self.get_error_type(error_message)
        if error_type == "AssertionError":
            return self.assertion_error_prompt(error_message, extract_test_case, change_test_case_entry, to_replace, entry_point)
        elif error_type == "NameError":
            return self.name_error_prompt(error_message)
        else:
            return self.generic_error_prompt(error_message, send_original)