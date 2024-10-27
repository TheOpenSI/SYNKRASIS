# Container requirements taken from https://github.com/open-compass/code-evaluator/blob/master/requirements/ds1000.txt

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from subprocess import CompletedProcess
import re

from services.PyCapsule.PyCapsule import PyCapsule
from services.Container.Container import Container
from services.Base import ServiceBase
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser_ds1000_gpt import parse_solution_ds1000_gpt
from utils.output_message_format.output_colour import print_pycapsule

class PyCapsule_DS1000(PyCapsule):
    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 **kwargs):
        """
        PyCapsule_DS1000 constructor.

        Args:
            pycasule_container (Container): Container object.
            llm (LLMBase): LLM object.
        """
        super().__init__(pycapsule_container, llm, **kwargs)
        
    
    def _set_prompt_paths(self):
        """
        Override the prompt paths for DS1000.
        """
        self.CODE_FIX_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts/code_fix_prompt_ds1000.txt")
        self.CODE_GEN_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts/code_gen_prompt_ds1000.txt")
        
        
    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        Creates main.py, task_id.py files in the mount_dir.
        Args:
            code (str): solution, LLM generated Function definition.
            user_query (dict): User query dictionary
        Metadata: FOR DS1000
            user_query = {
                    prompt: problem definition with snippet,
                    reference_code: reference solution,
                    metadata: {problem_id, library_problem_id, library, test_case_cnt, perturbation_type, perturbation_origin_id}
                    code_context = main.py file content, add solution = function definition\n result = funtion call, test function call
                }
        """ 
        # Suppress warning
        suppress_warning = self._suppress_warning_code()
        
        # Solution: generated function definition and result
        solution = ("solution = '''\n"
                    f"{code}\n'''\n")
        
        # Timeouts
        timeout = self._timeout_code(function_name = "test_execution", args = "(solution, )", timeout = 10) # passing args as string
        
        # Solution and test execution
        py_file_content = (f"{suppress_warning}\n"
                           f"{user_query['code_context']}\n" # test code
                           f"{solution}\n" # generated code
                           f"{timeout}") # timeout code
        
        # Main
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        self._create_py_file(main_py_path, py_file_content)

        # Task file
        metadata = user_query["metadata"]
        task_file_name = str(metadata["problem_id"]) + "_" + str(metadata["library_problem_id"]) + ".py"
        task_file_path = os.path.join(self.MOUNT_DIR, task_file_name)
        self._create_py_file(task_file_path, py_file_content)
        
           
    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None:
        """
        FOR DS1000.
        User query is a dictionary.

        Args:
            user_query (dict): Dictionary query to generate code, for structure refer to data/DS1000.py.
            suppress_conversation_history (bool): Suppress the conversation history, get activated when pycapsule is in fix mode.
        """
        if type(user_query) != dict:
            raise ValueError("user_query must be a dict for DS1000.")
        
        response = self.llm.generate_response(user_query["prompt"], 
                                              suppress_conversation_history = suppress_conversation_history)
        
        # Parsing
        code = parse_solution_ds1000_gpt(response)
        
        # Create main.py and task_id.py
        self._create_main_py(code, user_query)
        
        
    def _set_original_question(self, user_query: dict):
        """
        Overriden to handle dict user_query.

        Args:
            user_query (dict): user_query["prompt"] for DS1000.

        Returns:
            str: Original question extracted from user_query dict.
        """
        return user_query["prompt"]
    
    
    def _fix_code_with_data_point(self, response: CompletedProcess, data_point: dict) -> tuple[int, int]:
        """
        DS1000 specific fix code method.
        """
        return self._fix_code(response, data_point)
    
    
    def _fix_code(self, response: CompletedProcess, data_point: dict = None):
        """
        Gets activated only when response.returncode != 0.
        Will change sytem prompt and attempt to fix the code.
        From error response filters the traceback, assertion error and sends it to the LLM.
        Returns response code and number of attempts made.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
            data_point (dict): DS1000 data point reference.
            
        """
        print_pycapsule("Starting PyCapsule in fix mode.")
        
        attempt_count = 0
        return_code = -1
        
        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True)
            
            fix_mode_query = self.error_handling(error_message = response.stderr)
            
            # Updating response, main.py and requirements.txt
            fix_mode_data_point = data_point.copy()
            fix_mode_data_point["prompt"] = fix_mode_query
            self._generate_code(fix_mode_data_point, suppress_conversation_history = False)
            
            # Running the code
            response = self.container.start_container()
            attempt_count += 1
            return_code = response.returncode
        self._change_system_prompt() # Resetting the system prompt
        return return_code, attempt_count
    
    def cleanup(self):
        pass