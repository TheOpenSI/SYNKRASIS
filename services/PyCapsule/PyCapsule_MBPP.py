import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from subprocess import CompletedProcess

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_pycapsule


class PyCapsule_MBPP(PyCapsuleBase):
    def __init__(self, 
                 pycapsule_container: Container, 
                 llm: LLMBase,
                 maximum_attempts: int = 5) -> None:
        """
        PyCapsule for MBPP dataset.

        Args:
            pycasule_container (Container): Container object.
            llm (LLMBase): LLM object.
            maximum_attempts (int, optional): Maximum attempts to fix the code. Defaults to 5.
        """
        super().__init__(pycapsule_container, llm, maximum_attempts)
        
        
    def _set_prompt_paths(self) -> None:
        return self.helper_set_prompt_paths()
        
        
    def _create_test_function(self, test_list: list) -> str:
        """
        Create the test function using the test list.
        Function signature is `test_function()`.

        Args:
            test_list (list): list of test cases.

        Returns:
            str: test function with all test cases + call to the function.
        """
        all_tests =  "\t" + "\n\t".join(test_list)
        test_function = ("def test_function():\n"
                         f"{all_tests}\n")
        
        return test_function
        
        
    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        Create the main.py file.
        Uses suppress warning code and the timeout code.

        Args:
            code (str): code to be written to the main.py file.
            user_query (dict): Original user query dictionary.
        """
        # test cases
        test_function = self._create_test_function(user_query["test"])
        
        # timeout code
        timeout_code = self.timeout_code("test_function", "()", 10)
        
        # example call removal
        code = self.example_call_detection.extract_code_blocks(code)
        
        # content
        py_file_content = (self.suppress_warning_code() + "\n" +
                           code + "\n\n" +
                           test_function + "\n\n" +
                           timeout_code)
        
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        task_file_path = os.path.join(self.MOUNT_DIR, f"task_{user_query['task_id']}.py")
        
        self.create_py_file(main_py_path, py_file_content)
        self.create_py_file(task_file_path, py_file_content)
        
        
    def _generate_code(self, 
                       user_query: dict, 
                       suppress_conversation_history: bool = True) -> None:
        """
        FOR MBPP.
        User query is a dictionary.
        Generates the raw LLM response and parses the response to get the code. 
        Parser being used - utils.code_parsing.code_parser.parse_response for requirements, code

        Args:
            user_query (dict): Original user query dictionary.
            suppress_conversation_history (bool, optional): Omit conversation history. Defaults to True.
        """
        if type(user_query) != dict:
            raise ValueError("user_query must be a dictionary for MBPP.")
        
        llm_response = self.llm.generate_response(user_query["prompt"],
                                              suppress_conversation_history = suppress_conversation_history)
        
        requirements, code = parse_response(llm_response)
        self._create_main_py(code, user_query)
        self.create_requirements_txt(requirements)
        
        
    def _get_fix_mode_query(self, response: CompletedProcess, meta_data: dict) -> str:
        return self.error_handling(response.stderr)
    
    
    def _update_code(self, 
                     fix_mode_query: str, 
                     suppress_conversation_history: bool, 
                     meta_data: dict) -> None:
        data_point = meta_data.copy()
        data_point["prompt"] = fix_mode_query
        self._generate_code(data_point, suppress_conversation_history)
        
        
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
    
    
    def _call_fix_code(self, response: CompletedProcess, data_point: dict) -> tuple[int, int]:
        return self.fix_code(response, data_point)