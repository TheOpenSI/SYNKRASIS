import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from subprocess import CompletedProcess
import re

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_pycapsule

class PyCapsule_BigCodeBench(PyCapsuleBase):
    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5):
        """
        PyCapsule_BigCodeBench constructor.

        Args:
            pycasule_container (Container): Container object.
            llm (LLMBase): LLM object.
            maximum_attempts (int, optional): Maximum attempts to fix the code. Defaults to 5.
        """
        super().__init__(pycapsule_container, llm, maximum_attempts)
        
    
    def _set_prompt_paths(self):
        return super().helper_set_prompt_paths()
    
    
    def _create_main_py(self, code: str, user_query: dict) -> None: 
        # Suppress warning
        suppress_warning = self._suppress_warning_code()
        
        # Timeout code
        timeout_code = self._timeout_code(function_name = "unittest.main", 
                                          args_for_function = "()", 
                                          timeout = 10)
        
        # Content
        code_to_write = suppress_warning + "\n\n" + code + "\n\n" + user_query["test"] + "\n\n" + timeout_code
        
        # Main
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        self._create_py_file(main_py_path, code_to_write)

        # Task file
        task_file_name = user_query["task_id"].replace("/", "_") + ".py"
        task_file_path = os.path.join(self.MOUNT_DIR, task_file_name)
        self._create_py_file(task_file_path, code_to_write)
        
           
    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None: 
        response = self.llm.generate_response(user_query["prompt"], 
                                              suppress_conversation_history = suppress_conversation_history)
        
        # Parse the response
        _, code = parse_response(response)
        
        # Create main.py and task_id.py
        self._create_main_py(code, user_query)
        
        # Create requirements.txt
        # BigCodeBench has list of libraries in user_query["libs"]
        self._create_requirements_txt(user_query["libs"])
        
        
    def _get_fix_mode_query(self, response: CompletedProcess, meta_data: dict) -> str:
        pass
        # TODO: Fix error handling


    def _update_code(self, fix_mode_query: str, suppress_conversation_history: bool, meta_data: dict) -> None:
        data_point = meta_data.copy()
        data_point["prompt"] = fix_mode_query
        self._generate_code(data_point, suppress_conversation_history)
        
        
    def _set_original_question(self, user_query: dict) -> str:
        return user_query["prompt"]
    
    
    def _call_fix_code(self, response: CompletedProcess, data_point: dict) -> tuple[int, int]:
        return self.fix_code(response, data_point)