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
            pycasule_container (Container): Container object.
            llm (LLMBase): LLM object.
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
            user_query (dict): HumanEval data point reference.
        
        Metadata: HUMANEVAL data structure (from the data loader)
            user_query = {
                    "task_id": datapoint["task_id"],
                    "prompt": datapoint["prompt"],
                    "entry_point": datapoint["entry_point"],
                    "test": datapoint["test"]
                }
        """ 
        # Suppress warning
        suppress_warning = self._suppress_warning_code()
        
        # Timeout code
        timeout_code = self._timeout_code(function_name = "check", 
                                          args_for_function = f"({user_query['entry_point']}, )", 
                                          timeout = 10)
        
        # Content
        code_to_write = suppress_warning + "\n" + code + "\n\n" + user_query["test"] + "\n" + timeout_code
        
        # Main
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        self._create_py_file(main_py_path, code_to_write)

        # Task file
        task_file_name = user_query["task_id"].replace("/", "_") + ".py"
        task_file_path = os.path.join(self.MOUNT_DIR, task_file_name)
        self._create_py_file(task_file_path, code_to_write)
        
           
    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None:
        """
        HUMANEVAL implementation.
        User query is a dictionary.
        Calls the LLM to generate the code and requirements.

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
        """
        For HumanEval, LLM query is stored in user_query["prompt"].

        Args:
            user_query (dict): HumanEval data point reference.

        Returns:
            str: Query prompt for the LLM.
        """
        return user_query["prompt"]
    
    
    def _fix_code_with_data_point(self, response: CompletedProcess, data_point: dict) -> tuple[int, int]:
        """
        HumanEval implementation.
        Calls the fix code function to handle dict data_point.

        Args:
            response (CompletedProcess): Container response with stdout, stderr and return code.
            data_point (dict): HumanEval data point reference.

        Returns:
            tuple[int, int]: Return code and number of attempts made.
        """
        return self._fix_code(response, data_point)
    
    
    def _fix_code(self, response: CompletedProcess, data_point: dict = None) -> tuple[int, int]:
        """
        Gets activated only when response.returncode != 0.
        Will change sytem prompt and attempt to fix the code.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
            data_point (dict): HumanEval data point reference.
        
        Returns:
            tuple[int, int]: Return code and number of attempts made.
            
        """
        print_pycapsule("Starting PyCapsule in fix mode.")
        
        attempt_count = 0
        return_code = -1
        
        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True)
            
            # HumanEval  runs the test cases using check(candidate) so we need to replace candidate with the entry_point
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