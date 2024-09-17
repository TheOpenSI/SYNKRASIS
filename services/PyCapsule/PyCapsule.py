# CodeLlama based

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess
from subprocess import CompletedProcess
from typing import Union

from services.Base import ServiceBase
from services.Container.Container import Container
from services.Ollama.Ollama import Ollama
from utils.code_parsing.parse_codellama import parse_codellama
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_pycapsule, print_model_output

class PyCapsule(ServiceBase):
    def __init__(self, 
                 pycapsule_container: Container,
                 llm: Ollama,
                 maximum_attempts: int = 5):
        """
        PyCapsule service class for generating and validating code.
        Args:
            pycapsule_container (Container): Default container for PyCapsule service.
            llm (Ollama): Ollama Object for LLM, not supporting the LLM.
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
        self._change_system_prompt()
        self.maximum_attempts = maximum_attempts
        self.MOUNT_DIR = os.path.abspath(__file__).replace("PyCapsule.py", "../Container/mount_dir")


    def _change_system_prompt(self, is_fix_mode: bool = False):
        """
        Change the system promopt for code generation.
        Reads the prompt from a file.
        Args:
            is_fix_mode (bool, optional): If True, will change the prompt for fix mode. Defaults to False.
        """
        if not is_fix_mode:
            prompt_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_gen_prompt.txt")
        else:
            prompt_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_fix_prompt.txt")
            
        with open(prompt_file_path, "r") as file:
            code_gen_prompt = file.read().strip()
        self.llm.set_system_prompt(code_gen_prompt)
        
        
    def _create_requirements_txt(self, requirements: list) -> None:
        """
        Create requirements.txt file in the mount_dir.

        Args:
            requirements (list): List of requirements.
        """
        if not(len(requirements) == 1 and ("none" in requirements or "None" in requirements)):
            with open(os.path.join(self.MOUNT_DIR, "requirements.txt"), "w") as file:
                file.write('\n'.join(requirements))
                
                
    def _create_main_py(self, code: str, example: str, user_query: dict, ) -> None:
        """
        Only used for HumanEval or when user_query is a dictionary.
        Creates main.py file in the mount_dir.
        Args:
            code (str): Function definition.
            example (str): Example code, generated from test case.
            user_query (dict): User query dictionary
        """ 
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        # Suppress warning
        suppress_warning = ("import warnings\n"
                            "warnings.filterwarnings('ignore')\n")
        with open(main_py_path, "w") as file:
            file.write(suppress_warning + "\n\n" + code + "\n\n" + example + "\n\n" + user_query["test_code"])

        # Generate the task-specific py file
        task_file_name = user_query["task_id"].replace("/", "_") + ".py"
        task_file_path = os.path.join(self.MOUNT_DIR, task_file_name)

        with open(task_file_path, "w") as task_file:
            task_file.write(suppress_warning + "\n\n" + code + "\n\n" + example + "\n\n" + user_query["test_code"])
        
    
    def _generate_code_str(self, user_query: str, suppress_conversation_history: bool) -> None:
        """
        Generate response when user query is a string.

        Args:
            user_query (str): String query to generate code.
            suppress_conversation_history (bool): Suppress the conversation history, get activated when pycapsule is in fix mode.
        """
        response = self.llm.generate_response(user_query, 
                                              suppress_conversation_history = suppress_conversation_history)
        requirements, code, example = parse_codellama(response)
        
        # Create main.py
        with open(os.path.join(self.MOUNT_DIR, "main.py"), "w") as file:
            file.write(code + '\n\n' + example)
        
        # Create requirements.txt
        self._create_requirements_txt(requirements)
        
        
    def _generate_code_dict(self, user_query: dict, suppress_conversation_history: bool) -> None:
        """
        FOR HUMANEVAL.
        Generate response when user query is a dictionary.

        Args:
            user_query (dict): Dictionary query to generate code, for structure refer to data/HumanEval.py.
            suppress_conversation_history (bool): Suppress the conversation history, get activated when pycapsule is in fix mode.
        """
        response = self.llm.generate_response(user_query["prompt"], 
                                              suppress_conversation_history = suppress_conversation_history)
        
        # Parsing
        requirements, code, example = parse_codellama(response)
        
        # Time complexity
        example = ("import time\n"
                   "start_time = time.time()\n"
                   f"{user_query['time_complexity_test_code']}\n"
                   "end_time = time.time()\n"
                   "print(f'Execution time: {end_time - start_time} seconds')")
        
        # Create main.py with funtion defintion, time complexity code and test cases.
        self._create_main_py(code, example, user_query)
        
        # Create requirements.txt
        self._create_requirements_txt(requirements)
        
        
    def _fix_code(self, response: CompletedProcess, data_point: dict) -> int:
        """
        Gets activated only when response.returncode != 0.
        Will change sytem prompt and attempt to fix the code.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
        """
        print_pycapsule("Starting PyCapsule in fix mode.")
        attempt_count = 0
        response_code = -1
        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True) # Will chnage the system prompt and reset the chat history
            fix_mode_query = ("Your generated code had the following error -\n"
                              f"{response.stderr}\n") # TODO: Consider adding the code and example here
            
            # Updating response, main.py and requirements.txt
            if data_point:
                fix_mode_query = {
                    "prompt": fix_mode_query,
                    "task_id": data_point["task_id"],
                    "test_code": data_point["test_code"],
                    "time_complexity_test_code": data_point["time_complexity_test_code"]
                }
            self._generate_code(fix_mode_query, suppress_conversation_history = False)
            
            # Running the code
            response = self.container.start_container()
            attempt_count += 1
            response_code = response.returncode
        self._change_system_prompt() # Resetting the system prompt
        return response_code # TODO
        
    
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
        
        
    def _generate_code(self, user_query: Union[str, dict], suppress_conversation_history: bool = True):
        """
        Uses the Ollama object to generate code.
        Create main.py and requirements.txt files in the mount_dir.
        Args:
            user_query (str): User query to generate code.
        """
        if type(user_query) == str:
            self._generate_code_str(user_query, suppress_conversation_history)
        elif type(user_query) == dict:
            self._generate_code_dict(user_query, suppress_conversation_history)
        else:
            raise ValueError("user_query must be a dict or string.")
        
        
    def __call__(self, user_query: Union[str, dict]) -> int:
        """
        Generate code using ollama and run the code in the container.

        Args:
            user_query (Union[str, dict]): Either a datapoint as dict or string query.
        """
        # This will generate response from LLM and parse the response to get the code
        self.llm._set_seed()
        self._generate_code(user_query) # this creates the main.py and requirements.txt
        
        # Start the container
        response: CompletedProcess = self.container.start_container()
        flag = response.returncode
        if response.returncode != 0:
            print_error("Generated code returned a non-zero exit code. Starting pycapsule in fix mode.")
            data_point_ref = None if type(user_query) == str else user_query # Will send the whole data_point as reference
            self.llm._set_seed()
            flag = self._fix_code(response, data_point_ref)
            
            
        return flag
            

        
    # For testing only
    @staticmethod
    def run_command(command: str = "whoami") -> str:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()


    def cleanup(self):
        self.container.cleanup()
        self.llm.clear_chat_history()
        
        mount_dir = os.path.abspath(__file__).replace("PyCapsule.py", "../Container/mount_dir")
        # for file in ['main.py', 'requirements.txt']:
        #     file_path = os.path.join(mount_dir, file)
        #     if os.path.exists(file_path):
        #         os.remove(file_path)
        
        print_success("PyCapsule resources cleaned up.")