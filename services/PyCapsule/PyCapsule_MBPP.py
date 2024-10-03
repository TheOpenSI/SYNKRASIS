import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from subprocess import CompletedProcess

from services.PyCapsule.PyCapsule import PyCapsule
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_pycapsule
from utils.error_parsing.parse_error import parse_error_human_eval

class PyCapsule_MBPP(PyCapsule):
    def __init__(self, 
                 pycapsule_container: Container, 
                 llm: LLMBase):
        """
        PyCapsule for MBPP dataset.

        Args:
            pycasule_container (Container): Container object.
            llm (LLMBase): LLM object.
        """
        super().__init__(pycapsule_container, llm)
        
        
    def _set_prompt_paths(self) -> None:
        """
        Using the default prompts for MBPP.
        """
        super()._set_prompt_paths()
        
        
    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        Create the main.py file.
        Uses suppress warning code but not the timeout code.

        Args:
            code (str): code to be written to the main.py file.
            user_query (dict): data point with task_id, prompt, function_signature, test_list.
        """
        py_file_content = (self._suppress_warning_code() + "\n" +
                           code + "\n" +
                           "\n".join(user_query["test_list"]))
        
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        task_file_path = os.path.join(self.MOUNT_DIR, f"task_{user_query['task_id']}.py")
        
        self._create_py_file(main_py_path, py_file_content)
        self._create_py_file(task_file_path, code)
        
        
    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None:
        """
        FOR MBPP.
        User query is a dictionary.
        Generates the raw LLM response using the LLM object.
        Parses the response to get the code. 
        Parser being used - parse_response for requirements, code
        Use APPROPRIATE code parsing function.
        Creates the main.py file in the mountdir

        Args:
            user_query (dict): user query with task_id, prompt, function_signature, test_list.
            suppress_conversation_history (bool, optional): Omit conversation history. Defaults to True.
        """
        if type(user_query) != dict:
            raise ValueError("user_query must be a dictionary for MBPP.")
        
        llm_response = self.llm.generate_response(user_query["prompt"] + "\n" + user_query["function_signature"],
                                              suppress_conversation_history = suppress_conversation_history)
        
        requirements, code = parse_response(llm_response)
        self._create_main_py(code, user_query)
        self._create_requirements_txt(requirements)
        
        
    def _fix_code(self, response: CompletedProcess, data_point: dict = None) -> tuple[int, int]:
        """
        Gets activated only when response.returncode != 0.
        Will change sytem prompt and attempt to fix the code.
        From error response filters the traceback, assertion error and sends it to the LLM.
        Using HumanEval error parser.
        Returns response code and number of attempts made.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
            data_point (dict): MBPP data point reference.
            
        """
        print_pycapsule("Starting PyCapsule in fix mode.")
        
        attempt_count = 0
        return_code = -1
        
        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True)
            
            error_response = parse_error_human_eval(response, data_point, modify_assertion_error = False) # using the human eval error parser
            
            fix_mode_query = ("Your generated code had the following error -\n"
                              f"{error_response}\n")
            
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