import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from subprocess import CompletedProcess
import re

from services.PyCapsule.PyCapsule import PyCapsule
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_pycapsule

class PyCapsule_HumanEval(PyCapsule):
    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase):
        """
        PyCapsule_HumanEval constructor.

        Args:
            model_name (str): Model name.
            model_path (str): Model path.
            mount_dir (str): Mount directory.
            verbose (bool): Verbose mode.
        """
        super().__init__(pycapsule_container, llm)
        
    
    def _set_prompt_paths(self) -> None:
        """
        Override the prompt paths for HumanEval.
        """
        self.CODE_FIX_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts/code_fix_prompt_humaneval.txt")
        self.CODE_GEN_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts/code_gen_prompt_humaneval.txt")
        
        
    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        HumanEval implementation when user_query is a dictionary.
        Creates main.py, task_id.py files in the mount_dir.
        Args:
            code (str): Function definition.
            user_query (dict): User query dictionary
        Metadata: FOR HUMANEVAL
            user_query = {
                    "task_id": datapoint["task_id"],
                    "prompt": datapoint["prompt"],
                    "entry_point": datapoint["entry_point"],
                    "test": datapoint["test"],
                    "time_complexity_test_code": time_complexity_test_code,
                    "test_code": test_code
                }
        """ 
        # Suppress warning
        suppress_warning = self._suppress_warning_code()
        
        # Main
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        self._create_py_file(main_py_path, 
                             suppress_warning + "\n" + code + "\n" + "\n" + user_query["test_code"])

        # Task file
        task_file_name = user_query["task_id"].replace("/", "_") + ".py"
        task_file_path = os.path.join(self.MOUNT_DIR, task_file_name)
        self._create_py_file(task_file_path, 
                             suppress_warning + "\n" + code + "\n" + "\n" + user_query["test_code"])
        
           
    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None:
        """
        FOR HUMANEVAL.
        User query is a dictionary.

        Args:
            user_query (dict): Dictionary query to generate code, for structure refer to data/HumanEval.py.
            suppress_conversation_history (bool): Suppress the conversation history, get activated when pycapsule is in fix mode.
        """
        if type(user_query) != dict:
            raise ValueError("user_query must be a dict for HumanEval.")
        
        response = self.llm.generate_response(user_query["prompt"], 
                                              suppress_conversation_history = suppress_conversation_history)
        
        # Parsing
        requirements, code = parse_response(response)
        
        # Create main.py and task_id.py
        self._create_main_py(code, user_query)
        
        # Create requirements.txt
        self._create_requirements_txt(requirements)
        
        
    def _set_original_question(self, user_query: dict) -> str:
        return user_query["prompt"]
    
    
    def _fix_code_with_data_point(self, response: CompletedProcess, data_point: dict) -> tuple[int, int]:
        return self._fix_code(response, data_point)
    
    
    def _fix_code(self, response: CompletedProcess, data_point: dict = None) -> tuple[int, int]:
        """
        Gets activated only when response.returncode != 0.
        Will change sytem prompt and attempt to fix the code.
        From error response filters the traceback, assertion error and sends it to the LLM.
        Returns response code and number of attempts made.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
            data_point (dict): HumanEval data point reference.
            
        """
        print_pycapsule("Starting PyCapsule in fix mode.")
        
        attempt_count = 0
        return_code = -1
        
        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True)
            
            fix_mode_query = self.error_handling(error_message = response.stderr,
                                                 extract_test_case=True,
                                                 change_test_case_entry=True,
                                                 to_replace="candidate",
                                                 entry_point=data_point["entry_point"])
            
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