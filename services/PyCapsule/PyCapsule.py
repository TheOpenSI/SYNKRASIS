#===================================================================================================================================
# For child class to override:
# - _set_prompt_paths
# - _create_main_py
# - _fix_code
# - _generate_code
# - _set_original_question
# - _fix_code_with_data_point
#===================================================================================================================================
import os
import sys
import re
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess
from subprocess import CompletedProcess
from typing import Union, Tuple

from services.Base import ServiceBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_error, print_warning, print_success, print_pycapsule, print_model_output
from modules.ErrorHandling import ErrorHandling

class PyCapsule(ServiceBase):
    def __init__(self, 
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5):
        """
        PyCapsule service class for generating and validating code.
        Args:
            pycapsule_container (Container): Default container for PyCapsule service.
            llm (LLMBase): LLM
            maximum_attempts (int, optional): Maximum tries to fix generated code. Defaults to 3.

        Raises:
            ValueError: If chat history is not enabled in Ollama.
        """
        super().__init__()
        if not llm.enable_chat_history:
            print_error("Chat history must be enabled in the LLM object for PyCapsule service")
            raise ValueError("Chat history must be enabled in the LLM object for PyCapsule service")
        self.container = pycapsule_container
        self.llm = llm
        self.maximum_attempts = maximum_attempts
        self.MOUNT_DIR = os.path.abspath(__file__).replace("PyCapsule.py", "../Container/mount_dir")
        self._set_prompt_paths()
        self._change_system_prompt()
        self.error_handling = ErrorHandling(target_file_name= "/usr/src/app/main.py")
            
    def _suppress_warning_code(self) -> str:
        """
        Suppress warnings in the generated code.
        """
        return ("import warnings\n"
                "warnings.filterwarnings('ignore')\n")
        
        
    def _timeout_code(self, function_name: str, args: Tuple, timeout: int) -> str:
        """
        Runs the example call or the test cases in a different thread with a timeout period.
        In case of an infinite loop, the code will terminate the process and raise an exception.
        Infinite loop will raise Exception("Generated code is running infinite loop.")
        Rest of the errors will raise Exception("An error occurred. This is a generic error message. See previous error message")

        Args:
            function_name (str): function to run/test cases
            args (Tuple): arguments to pass to the function
            timeout (int): timeout period in seconds

        Raises:
            Exception: Infinite loop
            Exception: Other exceptions (Generic error message)

        Returns:
            str: Code snippet to run the function with timeout.
        """
        return ("from multiprocessing import Process\n"
                f"p: Process = Process(target = {function_name}, args = {args})\n"
                "p.start()\n"
                f"p.join(timeout = {timeout})\n"
                "if p.is_alive():\n"
                "    p.terminate()\n"
                "    raise Exception('Generated code is running infinite loop.')\n"
                "if p.exitcode != 0:\n"
                "    raise Exception('An error occurred. This is a generic error message. See previous error message')\n")
        
        
    def _set_prompt_paths(self):
        """
        Set the prompt paths for code generation and code fix.\n
        ** Override for dataset specific implementation.
        """
        self.CODE_GEN_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_gen_prompt.txt")
        self.CODE_FIX_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_fix_prompt.txt")


    def _change_system_prompt(self, is_fix_mode: bool = False):
        """
        Change the system promopt for code generation.
        Reads the prompt from a file.
        Args:
            is_fix_mode (bool, optional): If True, will change the prompt for fix mode. Defaults to False.
        """
        prompt_file_path = self.CODE_FIX_PROMPT_PATH if is_fix_mode else self.CODE_GEN_PROMPT_PATH
            
        with open(prompt_file_path, "r") as file:
            code_gen_prompt = file.read().strip()
        self.llm.set_system_prompt(code_gen_prompt)
        
        
    def _create_py_file(self, path: str, content:str) -> None:
        """
        Create a python file at specified path.
        Args:
            path (str): Path to create the file.
            content (str): Content to write in the file.
        """
        with open(path, "w") as task_file:
            task_file.write(content)
        
        
    def _create_requirements_txt(self, requirements: list) -> None:
        """
        Create requirements.txt file in the mount_dir.

        Args:
            requirements (list): List of requirements.
        """
        if requirements != []:
            with open(os.path.join(self.MOUNT_DIR, "requirements.txt"), "w") as file:
                file.write('\n'.join(requirements))
 
                
    def _create_main_py(self, code: str, test_cases:str = "") -> None:
        """
        Creates main.py file in the mount_dir. 
        This  just adds the LLM generated test cases (if any) to the py file.
        For dataset specific implementation, override this method so instead of test case: str, it can accept a user_query: dict.
        The user_query will contain the test cases and other metadata.\n
        ** Override for dataset specific implementation.
        
        Args:
            code (str): Function definition IDEALLY WITH AN EXAMPLE.
            test_cases (str): Test cases either generated using llm or custom. Defaults to "".
        """ 
        # Suppress warning
        suppress_warning = self._suppress_warning_code()
        
        # Main
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        self._create_py_file(main_py_path, suppress_warning + "\n\n" + code + "\n\n" + test_cases)
        
        
    def _fix_code(self, response: CompletedProcess) -> tuple[int, int]:
        """
        Gets activated only when response.returncode != 0.
        Will change sytem prompt and attempt to fix the code.
        Returns response code and number of attempts made.\n
        ** Override for dataset specific implementation.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
        Returns:
            tuple[int, int]: return code and number of attempts made.
        """ 
        print_pycapsule("Starting PyCapsule in fix mode.")
        
        attempt_count = 0
        return_code = -1
        
        # Comment: Danny, how is response assigned before the following loop?
        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True) # Changing the system prompt for fix mode
            
            # Error message after removing generic and external file error
            fix_mode_query = self.error_handling(error_message = response.stderr,
                                                 send_original = False,
                                                 extract_test_case = False,
                                                 change_test_case_entry = False)
            
            # Updating code
            self._generate_code(fix_mode_query, suppress_conversation_history = False)
            
            # Running the code
            response = self.container.start_container()
            
            attempt_count += 1
            return_code = response.returncode
        
        self._change_system_prompt() # Resetting the system prompt to normal mode
        
        return return_code, attempt_count
 
        
    def _generate_code(self, user_query: str, suppress_conversation_history: bool = True) -> None:
        """
        Create the main.py and requirements from the LLM response.
        USE APPROPRIATE PARSER.\n
        ** Override for dataset specific implementation.

        Args:
            user_query (str): String query to generate code.
            suppress_conversation_history (bool): Suppress the conversation history, get activated when pycapsule is in fix mode.
        """ 
        response = self.llm.generate_response(user_query, 
                                              suppress_conversation_history = suppress_conversation_history)
        requirements, code = parse_response(response) # see code_parsing/code_parser.py for structure.
        
        # Create main.py
        with open(os.path.join(self.MOUNT_DIR, "main.py"), "w") as file:
            file.write(code)
        
        # Create requirements.txt
        self._create_requirements_txt(requirements)
        
        
    def _set_original_question(self, user_query: str) -> str:
        """
        Set the original question for the chat history.\n
        ** OVERRIDE for dataset specific implementation.
        
        Args:
            user_query (Union[str, dict]): Either a datapoint as dict or string query.
        Returns:
            str: Original question.
        """
        if isinstance(user_query, str):
            return user_query
        else:
            raise NotImplementedError("Override this method in the child class for dict type user_query.")
        
        
    def _fix_code_with_data_point(self, response: CompletedProcess, data_point: Union[str, dict]) -> tuple[int, int]:
        """
        Calls the fix code method\n
        ** OVERRIDE for dataset specific implementation.
        """
        if isinstance(data_point, dict):
            raise NotImplementedError("Override this method in the child class for dict type data_point.")
        
        return self._fix_code(response)
        
        
    def __call__(self, user_query: Union[str, dict]) -> tuple[int, int]:
        """
        Generate code using LLM and run the code in the container.

        Args:
            user_query (Union[str, dict]): Either a datapoint as dict or string query.
        """
        # Override for dataset specific implementation.
        original_question = self._set_original_question(user_query)
        
        # Initialize the chat history
        self.llm._init_chat_history(original_question)
        
        # Creates the main.py and requirements.txt
        self._generate_code(user_query)
        
        # Start the container
        fix_mode_attempts = 0 # Number of attempts made in fix mode
        
        # Container response
        response: CompletedProcess = self.container.start_container()
        
        flag = response.returncode # 0 if code runs successfully
        
        if response.returncode != 0:
            print_error("Generated code returned a non-zero exit code. Starting pycapsule in fix mode.")
            # Use parent implementation of _fix_code()
            # For str user query, this will work as expected.
            # For dict user query, override _call_fix_code() in the child class, otherwise it will raise NotImplementedError.
            flag, fix_mode_attempts = self._fix_code_with_data_point(response, user_query)
            
        self.llm.clear_chat_history()
            
        return flag, fix_mode_attempts
            

    # For testing only
    @staticmethod
    def run_command(command: str = "whoami") -> str:
        """
        For TESTING only.
        Runs whoami command in the local shell.

        Args:
            command (str, optional): Command to run. Defaults to "whoami".

        Returns:
            str: Output of the command.
        """
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    
    
    @staticmethod
    def _debug_insert_error():
        """
        For TESTING only.
        Inserts syntax error in the generated code.
        """
        mount_dir = os.path.abspath(__file__).replace("PyCapsule.py", "../Container/mount_dir")
        with open(os.path.join(mount_dir, "main.py"), "r") as file:
            data = file.readlines()
        file.close()
        new_data = []
        for v in data:
            if v.find("def ") > -1:
                # v = v + "\t'my_str'.append(a)\n"
                v = v.replace("(", "((")
            new_data.append(v)
        # write
        with open(os.path.join(mount_dir, "main.py"), "w") as file:
            file.writelines(new_data)
        file.close()


    def cleanup(self):
        """
        Cleanup the resources used by PyCapsule.
        """
        self.container.cleanup()
        self.llm.clear_chat_history()
        
        for file in ['main.py', 'requirements.txt']:
            file_path = os.path.join(self.MOUNT_DIR, file)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        print_success("PyCapsule resources cleaned up.")