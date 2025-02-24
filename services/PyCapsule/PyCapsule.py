# ==================================================================================================
# PyCapsule general usage implementation.
# See PyCapsuleBase for more details.
# Changed system prompt to generate 2 test cases - 
# "In the code section, write exactly 2 test cases in a function called ‘test_program()’"
# Usage:
#     - pycapsule(user_query)
# ==================================================================================================

import os
import sys
import re

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess
from subprocess import CompletedProcess
from typing import Union, Tuple

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_warning

class PyCapsule(PyCapsuleBase):
    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5):
        """
        PyCapsule general service class for generating and validating code.
        Args:
            pycapsule_container (Container): Default container for PyCapsule service.
            llm (LLMBase): LLM
            maximum_attempts (int, optional): Maximum tries to fix generated code. Defaults to 3.

        Raises:
            ValueError: If chat history is not enabled in LLM.
        """
        super().__init__(pycapsule_container = pycapsule_container, 
                         llm = llm, 
                         maximum_attempts = maximum_attempts)


    def _set_prompt_paths(self):
        super().helper_set_prompt_paths()


    def _create_main_py(self, code: str, test_cases: str = "") -> None:
        if test_cases != "":
            print_warning("General Pycapsule does not support test cases.")
            
        # Suppress warning
        suppress_warning = self.suppress_warning_code()

        # Main
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        # Remove any example calls
        clean_code = self.example_call_detection.extract_code_blocks(code)
        time_safe_thread = self.timeout_code(function_name="test_program",
                                             args_for_function="()",
                                             timeout=10)
        py_content = (suppress_warning 
                      + "\n\n" 
                      + clean_code 
                      + "\n\n" 
                      + time_safe_thread)
        self.create_py_file(main_py_path, py_content)


    def _generate_code(self, 
                       user_query: str, 
                       suppress_conversation_history: bool = True) -> None:
        response = self.llm.generate_response(
            user_query,
            suppress_conversation_history=suppress_conversation_history
            )
        
        # Parse the response
        requirements, code = parse_response(response)

        # Create main.py
        self._create_main_py(code)
        
        # Create requirements.txt
        self.create_requirements_txt(requirements)
        
        
    def _get_fix_mode_query(self, response: CompletedProcess, meta_data: dict) -> str:
        # General query won't use the meta_data.
        return self.error_handling(error_message = response.stderr)
    
    
    def _update_code(self, 
                     fix_mode_query: str, 
                     suppress_conversation_history: bool, 
                     meta_data: dict) -> None:
        # General query won't use the meta_data.
        self._generate_code(fix_mode_query, suppress_conversation_history)
    

    def _set_original_question(self, user_query: str) -> str:
        if isinstance(user_query, str):
            return user_query
        else:
            raise NotImplementedError("General Pycapsule does not support dict type user query.")


    def _call_fix_code(self, response: CompletedProcess, 
                       data_point: Union[str, dict]) -> tuple[int, int]:
        return self.fix_code(response, data_point)