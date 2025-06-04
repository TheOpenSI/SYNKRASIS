# ============================================================================================
# PyCapsule for HumanEval.
# Using default parser: utils.code_parsing.code_parser - parse_response
# ============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from subprocess import CompletedProcess

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_pycapsule, print_error, print_warning

class PyCapsuleHE(PyCapsuleBase):
    def __init__(self,
                 container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5,
                 **kwargs) -> None:
        super().__init__(pycapsule_container=container,
                         llm=llm,
                         maximum_attempts=maximum_attempts,
                         **kwargs)
        
    @staticmethod
    def _validate_metadata(function_name: str,
                           meta_data: dict,
                           check_dict_keys: list[str]) -> None:
        """
        Helper function to check meta data compatibility.
        Prints and raises error if meta data is not provided or not in dict.

        Args:
            function_name (str): Name of the function where the error occurred.
            meta_data (dict): Meta data dictionary.
            check_dict_keys (list[str]): List of keys to check in the meta data dictionary.
        """
        if meta_data is None:
            print_error((f"Meta data is required for HumanEval in function: {function_name}, "
                          "pass the problem data-point as metadata"))
            raise ValueError((f"Meta data is required for HumanEval in function: {function_name}, "
                               "pass the problem data-point as metadata"))
        
        if not isinstance(meta_data, dict):
            print_error((f"Meta data must be a dictionary for HumanEval in function: {function_name}, "
                          "pass the problem data-point as metadata"))
            raise ValueError((f"Meta data must be a dictionary for HumanEval in function: {function_name}, "
                              "pass the problem data-point as metadata"))
        
        if not all(key in meta_data for key in check_dict_keys):
            print_error(("Not all required keys are present in the meta data for HumanEval in "
                        f"function: {function_name}, required keys: {check_dict_keys}"))
            raise ValueError(("Not all required keys are present in the meta data for HumanEval in "
                             f"function: {function_name}, required keys: {check_dict_keys}"))
        
        
    def _set_prompt_paths(self) -> None:
        self.helper_set_prompt_paths()
        
    
    def _create_main_py(self, 
                        code: str, 
                        test_cases: str, 
                        meta_data: dict) -> None:
        self._validate_metadata(function_name="_create_main_py",
                                meta_data=meta_data,
                                check_dict_keys=["entry_point", "test", "task_id"])
        
        if test_cases:
            print_warning("Test cases are not required for HumanEval, ignoring the test cases")
            
        # HumanEval's test function is called check
        time_safe_thread = self.timeout_code(function_name="check", 
                                             args_for_function=f"({meta_data['entry_point']}, )", 
                                             timeout=self.timeout)
        
        sanitised_code = self.example_call_detection.extract_code_blocks(code)
        py_file_content = (self.suppress_warning_code() +
                           "\n\n" +
                           sanitised_code +
                           "\n\n" +
                           meta_data["test"] +
                           "\n\n" +
                           time_safe_thread)
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        
        task_id = meta_data["task_id"].replace("/", "_")
        task_file_path = os.path.join(self.MOUNT_DIR, f"task_{task_id}.py")
        
        for file_path in [main_py_path, task_file_path]:
            self.create_py_file(file_path, py_file_content)
            
            
    def _generate_code(self, 
                       user_query: dict, 
                       suppress_conversation_history: bool = True) -> None:
        self._validate_metadata(function_name="_generate_code",
                                meta_data=user_query,
                                check_dict_keys=["prompt"])
        
        llm_response = self.llm.generate_response(user_prompt=user_query["prompt"], 
                                                  context=None, 
                                                  suppress_conversation_history=suppress_conversation_history)
        
        requirements, code = parse_response(llm_response)
        self._create_main_py(code=code, test_cases="", meta_data=user_query)
        self.create_requirements_txt(requirements)
        
        
    def _get_fix_mode_query(self, 
                            response: CompletedProcess, 
                            meta_data: dict) -> str:
        self._validate_metadata(function_name="_get_fix_mode_query",
                                meta_data=meta_data,
                                check_dict_keys=["entry_point"])
        
        return self.error_handling(error_message=response.stderr,
                                extract_test_case=True,
                                change_test_case_entry=True,
                                to_replace="candidate", # Specific to HumanEval.
                                entry_point=meta_data["entry_point"])
        
        
    def _update_code(self, 
                     fix_mode_query: str, 
                     suppress_conversation_history: bool, 
                     meta_data: dict) -> None:
        self._validate_metadata(function_name="_update_code",
                                meta_data=meta_data,
                                check_dict_keys=["prompt"])
        
        temp_data_point = meta_data.copy()
        temp_data_point["prompt"] = fix_mode_query
        self._generate_code(temp_data_point, suppress_conversation_history)
        
        
    def _set_original_question(self, user_query: dict) -> str:
        self._validate_metadata(function_name="_set_original_question",
                                meta_data=user_query,
                                check_dict_keys=["prompt"])
        
        return user_query["prompt"]
    
    
    def _call_fix_code(self, 
                       response: CompletedProcess, 
                       user_query: dict) -> tuple[int, int]:
        self._validate_metadata(function_name="_call_fix_code",
                                meta_data=user_query,
                                check_dict_keys=[])
        
        return self.fix_code(response, user_query)
        