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

class PyCapsule_HE(PyCapsuleBase):
    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5) -> None:
        super().__init__(pycapsule_container, llm, maximum_attempts)
        
        
    def _set_prompt_paths(self) -> None:
        self.helper_set_prompt_paths()


    def _create_main_py(self, 
                        code: str,
                        user_query: dict) -> None:
        # HumanEval's test function is called check
        # timeout code
        time_safe_thread = self.timeout_code(function_name="check", 
                                             args_for_function=f"({user_query['entry_point']}, )", 
                                             timeout=self.timeout)
        
        # example call removal
        sanitised_code = self.example_call_detection.extract_code_blocks(code)
        
        # content
        py_file_content = (self.suppress_warning_code() + "\n\n" +
                           sanitised_code + "\n\n" +
                           user_query["test"] + "\n\n" +
                           time_safe_thread)
        
        # file path
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        task_file_path = os.path.join(self.MOUNT_DIR, f"he_task_{user_query['task_id']}.py")
        
        self.create_py_file(main_py_path, py_file_content)
        self.create_py_file(task_file_path, py_file_content)


    def _generate_code(self, 
                       user_query: dict, 
                       suppress_conversation_history: bool = True) -> None:
        self.validate_metadata(expected_type = dict,
                               meta_data = user_query)
        
        llm_response = self.llm.generate_response(user_prompt=user_query["prompt"],
                                                  suppress_conversation_history=suppress_conversation_history)
        
        requirements, code = parse_response(llm_response)
        self._create_main_py(code=code, user_query=user_query)
        self.create_requirements_txt(requirements)
        
        
    def _get_fix_mode_query(self, 
                            response: CompletedProcess, 
                            meta_data: dict) -> str:
        return self.error_handling(error_message = response.stderr,
                                   send_original = False,
                                   extract_test_case = True,
                                   change_test_case_entry = True,
                                   to_replace = "candidate", # Specific to HumanEval.
                                   entry_point = meta_data["entry_point"])
        
        
    def _update_code(self, 
                     fix_mode_query: str, 
                     suppress_conversation_history: bool, 
                     meta_data: dict) -> None:
        data_point = meta_data.copy()
        data_point["prompt"] = fix_mode_query
        self._generate_code(data_point, suppress_conversation_history)
        
        
    def _set_original_question(self, user_query: dict) -> str:
        return user_query["prompt"]


    def _call_fix_code(self, 
                       response: CompletedProcess, 
                       user_query: dict) -> tuple[int, int]:
        self.validate_metadata(expected_type = dict,
                               meta_data=user_query,
                               check_dict_keys=["task_id", "prompt", "entry_point", "test"])
        
        return self.fix_code(response, user_query)