import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from subprocess import CompletedProcess

from services.PyCapsule.PyCapsule import PyCapsule
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_pycapsule
from modules.ErrorHandling import ErrorHandling

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
        
        
    def _create_test_function(self, test_list: list) -> str:
        """
        Create the test function using the test list.
        Function signature is test_function().

        Args:
            test_list (list): list of test cases.

        Returns:
            str: test function with all test cases + call to the function.
        """
        all_tests =  "\t" + "\n\t".join(test_list)
        test_function = ("def test_function():\n"
                         f"{all_tests}\n"
                         "\n")
        
        return test_function
        
        
    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        Create the main.py file.
        Uses suppress warning code and the timeout code.

        Args:
            code (str): code to be written to the main.py file.
            user_query (dict): data point with task_id, prompt, function_signature, test_list.
        """
        test_function = self._create_test_function(user_query["test_list"])
        timeout_code = self._timeout_code("test_function", "()", timeout = 10)
        py_file_content = (self._suppress_warning_code() + "\n" +
                           code + "\n\n" +
                           test_function + "\n\n" +
                           timeout_code)
        
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        task_file_path = os.path.join(self.MOUNT_DIR, f"task_{user_query['task_id']}.py")
        
        self._create_py_file(main_py_path, py_file_content)
        self._create_py_file(task_file_path, py_file_content)
        
        
    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None:
        """
        FOR MBPP.
        User query is a dictionary.
        Generates the raw LLM response and parses the response to get the code. 
        Parser being used - utils.code_parsing.code_parser.parse_response for requirements, code

        Args:
            user_query (dict): user query with task_id, prompt, function_signature, test_list.
            suppress_conversation_history (bool, optional): Omit conversation history. Defaults to True.
        """
        if type(user_query) != dict:
            raise ValueError("user_query must be a dictionary for MBPP.")
        
        llm_response = self.llm.generate_response(user_query["prompt"],
                                              suppress_conversation_history = suppress_conversation_history)
        
        requirements, code = parse_response(llm_response)
        self._create_main_py(code, user_query)
        self._create_requirements_txt(requirements)
        
        
    def _set_original_question(self, user_query: dict) -> str:
        """
        For MBPP, LLM query is stored in user_query["prompt"].
        Overriden to handle dict user_query.

        Args:
            user_query (dict): user_query["prompt"] for MBPP.

        Returns:
            str: Original question extracted from user_query dict.
        """
        return user_query["prompt"]
    
    
    def _fix_code_with_data_point(self, response: CompletedProcess, data_point: dict) -> tuple[int, int]:
        """
        Calls the fix code function to handle dict data_point.
        """
        return self._fix_code(response, data_point)
        
        
    def _fix_code(self, response: CompletedProcess, data_point: dict = None) -> tuple[int, int]:
        """
        Gets activated only when response.returncode != 0.
        Will change sytem prompt and attempt to fix the code.
        Returns response code and number of attempts made.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
            data_point (dict): MBPP data point reference.
            
        Returns:
            tuple[int, int]: return code, number of attempts made.
            
        """
        print_pycapsule("Starting PyCapsule in fix mode.")
        
        attempt_count = 0
        return_code = -1
        
        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True)
            
            fix_mode_query = self.error_handling(error_message=response.stderr,
                                                 send_original=False,
                                                 extract_test_case=True,
                                                 change_test_case_entry=False)
            
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