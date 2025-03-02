# =============================================================================================
# Usage:
# - helper_set_prompt_paths()
#       Helper function to set the default prompt paths for code generation and 
#       code fix system prompts.
# - suppress_warning_code()
#       Code block to suppress warnings in the generated code.
# - timeout_code(function_name: str, args_for_function: str, timeout: int = 10)
#       Runs the example call or the test cases in a different thread with a timeout period.
# - create_py_file(path: str, content: str)
#       HELPER FUNCTION FOR create_main_py.
#       Creates a python file at specified path using the provided content.
# - create_requirements_txt(requirements: list)
#       Create requirements.txt file in the mount_dir.
# - fix_code(response: CompletedProcess, meta_data_dict: dict)
#       Gets activated only when response.returncode != 0.
#       Will change system prompt, user query and attempt to fix the code.
# - run_pycapsule_experiment(dataset: DatasetBase)
#       Runs the PyCapsule on the dataset.
# - cleanup()
#
# Abstract mehtods:
# - _set_prompt_paths
# - _create_main_py
# - _generate_code
# - _get_fix_mode_query
# - _update_code
# - _set_original_question
# - _call_fix_code
# =============================================================================================

import os
import sys
import re

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess
from subprocess import CompletedProcess
from typing import Union, Tuple
from abc import abstractmethod

from services.Base import ServiceBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from data.DatasetBase import DatasetBase
from utils.output_message_format.output_colour import print_error, print_warning
from utils.output_message_format.output_colour import print_success, print_pycapsule, print_model_output
from modules.ErrorHandling import ErrorHandling
from modules.ExampleCallDetection import ExampleCallDetection
from modules.ChatHistory import ChatHistory


class PyCapsuleBase(ServiceBase):
    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5,
                 timeout: int = 10,
                 target_file_name: str = "/usr/src/app/main.py"):
        """
        PyCapsule service class for generating and validating code.
        Args:
            pycapsule_container (Container): Container for PyCapsule service.
            llm (LLMBase): Select the LLM model for code generation.(HF_LLM|Ollama|OpenAI_GPT)
            maximum_attempts (int, optional): Maximum debugging attempts. Defaults to 5.
            timeout (int, optional): Timeout period for time safe thread. Defaults to 10.
            target_file_name (str, optional): Target file name for error handling clipping. 
                Defaults to "/usr/src/app/main.py".

        Raises:
            ValueError: If chat history is not enabled in LLM.
        """
        ServiceBase.__init__(self)
        # LLm validation
        self._validate_llm(llm)
        
        self.container = pycapsule_container
        self.llm = llm
        self.maximum_attempts = maximum_attempts
        self.timeout = timeout
        self.MOUNT_DIR = self.container.MOUNT_DIR_PATH
        
        self._set_prompt_paths()
        self._change_system_prompt(is_fix_mode = False)
        
        # Modules
        self.error_handling = ErrorHandling(target_file_name = target_file_name)
        self.example_call_detection = ExampleCallDetection()
        
        
    @abstractmethod    
    def _set_prompt_paths(self):
        """
        Set the prompt paths for code generation and code fix system prompts.
        """
        pass
    
    
    @abstractmethod
    def _create_main_py(self, 
                        code: str, 
                        test_cases: str, 
                        meta_data: dict = None) -> None:
        """
        Curate the main.py file.
        Process all its content here, e.g. add suppress warning code, timeout code, test cases etc.
        Use create_py_file() to create the main.py file and task specific py file as required.

        Args:
            code (str): Function definition IDEALLY WITH AN EXAMPLE.
            test_cases (str): Test cases either generated using llm or custom. Defaults to "".
            meta_data (dict): Pass the whole problem data point here, 
                useful for dataset specific implementation.
        """
        # NOTE: For child classes, create task specific py file here.
        pass
    
    
    @abstractmethod
    def _generate_code(self, 
                       user_query: Union[str, dict], 
                       suppress_conversation_history: bool = True) -> None:
        """
        Use llm.generate_response() here to generate LLM response/code.\n
        Use APPROPRIATE PARSER for code extraction.\n
        Use create_main_py() and create_requirements_txt() to create the files.

        Args:
            user_query (str): User query to generate code.
            suppress_conversation_history (bool): Suppress the conversation history, get activated when 
                pycapsule is in fix mode.
        """
        pass
    
    
    @abstractmethod
    def _get_fix_mode_query(self, response: CompletedProcess, meta_data: dict) -> str:
        """
        Apply necessary error handling using the self.error_handling object to get the fix mode query.
        Use the self.error_handling object to extract the error message from the response.
        
        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
            meta_data (dict): Metadata for the fix mode query, useful for dataset specific implementation.
                e.g. HumanEval.
            
        Returns:
            fix_mode_query (str): Fix mode query to debug the code.
        """
        pass
    
    
    @abstractmethod
    def _update_code(self, fix_mode_query: str, 
                     suppress_conversation_history: bool, 
                     meta_data: dict) -> None:
        """
        Only gets activated in Fix mode.\n
        Use self._generate_code() to generate fix mode response and 
            update main.py file in the container.\n
        If self._generated_code() expects a dict, update metadata's prompt.\n

        Args:
            fix_mode_query (Union[str, dict]): Can be the query itself as str or a dict with metadata.
            suppress_conversation_history (bool): Suppress the conversation history.
            meta_data (dict): Metadata for the fix mode query, useful for dataset specific implementation.
        """
        pass
    
    
    @abstractmethod
    def _set_original_question(self, user_query: Union[str, dict]) -> str:
        """
        Set the original question for the chat history.

        Args:
            user_query (Union[str, dict]): Either a datapoint as dict or string query.
        
        Returns:
            Original_Question (str): Original question.
        """
        pass
    
    
    @abstractmethod
    def _call_fix_code(self, 
                       response: CompletedProcess, 
                       data_point: Union[str, dict]) -> tuple[int, int]:
        """
        Calls the fix_code method with or without "meta_data_dict".
        Provides the ability to add (meta data: dict) for dataset specific implementation.
        "meta_data_dict"  defaults to None for general usage.
        
        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
            data_point (Union[str, dict]): Either a datapoint as dict or string query.
        """
        pass
    
    
    def helper_set_prompt_paths(self) -> None:
        """
        Helper for self._set_prompt_paths.
        Sets the default prompt paths - "prompts/code_gen_prompt.txt" and "prompts/code_fix_prompt.txt" 
            for code generation and code fix.
        """
        self.CODE_GEN_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "prompts/code_gen_prompt.txt")
        self.CODE_FIX_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "prompts/code_fix_prompt.txt")
    

    def suppress_warning_code(self) -> str:
        """
        Code block to suppress warnings in the generated code.
        """
        return ("import warnings\n"
                "warnings.filterwarnings('ignore')\n")
        
        
    def timeout_code(self, function_name: str, args_for_function: str, timeout: int = 10) -> str:
        """
        Runs the example call or the test cases in a different thread with a timeout period.\n
        In case of an infinite loop, the code will terminate the process and raise an exception.\n
        Infinite loop will raise Exception("Generated code is running infinite loop.")\n
        Rest of the errors will raise Exception("An error occurred. This is a generic error message. 
            See previous error message")

        Args:
            function_name (str): function to run/test cases
            args (str): arguments to pass to the function, FORMAT as a tuple, e.g. "(1, 2) or ()"
            timeout (int): timeout period in seconds

        Raises:
            Exception: Infinite loop
            Exception: Other exceptions (Generic error message)

        Returns:
            timeout_code (str): Code snippet to run the function with timeout.
        """
        return ("from multiprocessing import Process\n"
                f"p: Process = Process(target = {function_name}, args = {args_for_function})\n"
                "p.start()\n"
                f"p.join(timeout = {timeout})\n"
                "if p.is_alive():\n"
                "    p.terminate()\n"
                "    raise Exception('Generated code is running infinite loop.')\n"
                "if p.exitcode != 0:\n"
                "    raise Exception('An error occurred. This is a generic error message. "
                "See previous error message')\n")


    def create_py_file(self, path: str, content: str) -> None:
        """
        HELPER FUNCTION FOR create_main_py.\n
        Creates a python file at specified path using the provided content.

        Args:
            path (str): Path to create the file.
            content (str): Content to write in the file.
        """
        with open(path, "w") as task_file:
            task_file.write(content)


    def create_requirements_txt(self, requirements: list) -> None:
        """
        Create requirements.txt file in the mount_dir.

        Args:
            requirements (list): List of requirements.
        """
        if not (len(requirements) == 1 and "none" in requirements[0].lower()):
            with open(os.path.join(self.MOUNT_DIR, "requirements.txt"), "w") as file:
                file.write('\n'.join(requirements))
                
                
    def fix_code(self, 
                 response: CompletedProcess, 
                 meta_data_dict: dict = None) -> tuple[int, int]:
        """
        Gets activated only when response.returncode != 0.
        Will change system prompt, user query and attempt to fix the code.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
        Returns:
            Tuple (tuple[int, int]): return code and number of attempts made.
        """
        print_pycapsule("Starting PyCapsule in fix mode.")

        attempt_count = 0
        return_code = -1

        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True)  # Changing the system prompt for fix mode
            
            # Apply error handling to get the fix mode query
            # fix_mode_query = self._get_fix_mode_query(response, meta_data_dict)

            # Debugging span experiment
            fix_mode_query, suppress_flag = (self._fresh_start()
                                             if attempt_count % 3 == 0
                                             else (self._get_fix_mode_query(response, meta_data_dict),
                                                   False))
            
            # Updating code in container based on fix mode response
            self._update_code(fix_mode_query = fix_mode_query, 
                              suppress_conversation_history=suppress_flag,
                              meta_data = meta_data_dict)

            # Running the code
            response = self.container.start_container()
            
            # Debug attemps
            attempt_count += 1
            return_code = response.returncode

        self._change_system_prompt()  # Resetting the system prompt to normal mode

        return return_code, attempt_count
    
    
    def _fresh_start(self) -> None:
        """
        Clear chat history but keep the original question

        Args:
            conversation_history (ChatHistory): Chat history object of the LLM.
        """
        self._change_system_prompt(is_fix_mode=False)
        prompt = self.llm.chat_history.original_question
        self.llm.clear_chat_history()
        return prompt, True # To suppress the conversation history
                        
                
    def _validate_llm(self, llm: LLMBase):
        """
        Validate LLM configuration.
        LLM must have chat history enabled.
        """
        if not llm.enable_chat_history:
            print_error("Chat history must be enabled for LLM.")
            raise ValueError("Chat history must be enabled for LLM.")
                
                
    def _change_system_prompt(self, is_fix_mode: bool = False):
        """
        Changes the system prompt for code generation.
        Reads the prompt from a file.
        Args:
            is_fix_mode (bool, optional): If True, will change the prompt for fix mode. Defaults to False.
        """
        prompt_file_path = self.CODE_FIX_PROMPT_PATH if is_fix_mode else self.CODE_GEN_PROMPT_PATH

        with open(prompt_file_path, "r") as file:
            code_gen_prompt = file.read().strip()
        self.llm.set_system_prompt(code_gen_prompt)


    def __call__(self, user_query: Union[str, dict]) -> tuple[int, int]:
        """
        Generate code using LLM and run the code in the container.

        Args:
            user_query (Union[str, dict]): Either a datapoint as dict or string query.
            
        Returns:
            Tuple (tuple[int, int]): return code and number of attempts made.
        """
        # Set the original question in LLM's chat history
        original_question = self._set_original_question(user_query)

        # Initialize the chat history
        self.llm.init_chat_history(original_question)
        
        # Creates the main.py and requirements.txt
        self._generate_code(user_query)

        # Start the container
        fix_mode_attempts = 0  # Number of attempts made in fix mode

        # Container response
        response: CompletedProcess = self.container.start_container()

        flag = response.returncode  # 0 if code runs successfully

        if response.returncode != 0:
            print_error("Generated code returned a non-zero exit code. Starting pycapsule in fix mode.")
            # Fix mode
            flag, fix_mode_attempts = self._call_fix_code(response, user_query)

        self.llm.clear_chat_history()

        return flag, fix_mode_attempts
    
    
    def run_pycapsule_experiment(self, dataset: DatasetBase) -> None:
        """
        For experimental use only.
        Runs the PyCapsule on the dataset.
        
        Args:
            dataset (DatasetBase): Dataset to run the PyCapsule on.
        """
        
        while True:
            data_point = dataset.get_next()
            if data_point is None:
                break
            
            solve_flag, fix_mode_attempt_count = self.__call__(data_point)
            status = "fail"
            
            if solve_flag == 0:
                dataset.solved_count += 1
                status = "pass"
            else:
                dataset.unsolved_count += 1
                
            dataset.append_result(
                task_id=data_point["task_id"],
                fix_mode_attempt_count = fix_mode_attempt_count,
                status = status
            )
            
            print("#" * 50)
            print(f"Solved {dataset.solved_count} problems, Unsolved {dataset.unsolved_count} problems")
            print("#" * 50)
        
        dataset.log_to_csv(model_name = self.llm.model_name)

    
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
       
# ================================================================================================================
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
def debug_insert_error():
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