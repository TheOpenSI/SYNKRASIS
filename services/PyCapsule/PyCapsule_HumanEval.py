# CodeLlama based

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess
from subprocess import CompletedProcess
from typing import Union

from services.PyCapsule.PyCapsule import PyCapsule
from services.Container.Container import Container
from services.Ollama.Ollama import Ollama
from utils.code_parsing.parse_codellama import parse_codellama
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_pycapsule, print_model_output

class PyCapsule_HumanEval(PyCapsule):
    def _create_main_py(self, code: str, user_query: dict, ) -> None:
        """
        Only used for HumanEval or when user_query is a dictionary.
        Creates main.py file in the mount_dir.
        Args:
            code (str): Function definition.
            example (str): Example code, generated from test case.
            user_query (dict): User query dictionary
        """ 
        # Suppress warning
        suppress_warning = ("import warnings\n"
                            "warnings.filterwarnings('ignore')\n")
        
        # Main
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        self._create_py_file(main_py_path, suppress_warning + "\n\n" + code + "\n\n" + user_query["test_code"]) # TODO: Add time complexity code

        # Task file
        task_file_name = user_query["task_id"].replace("/", "_") + ".py"
        task_file_path = os.path.join(self.MOUNT_DIR, task_file_name)
        self._create_py_file(task_file_path, suppress_warning + "\n\n" + code + "\n\n" + user_query["test_code"])
        
           
    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None:
        """
        FOR HUMANEVAL.
        Generate response when user query is a dictionary.

        Args:
            user_query (dict): Dictionary query to generate code, for structure refer to data/HumanEval.py.
            suppress_conversation_history (bool): Suppress the conversation history, get activated when pycapsule is in fix mode.
        """
        if type(user_query) != dict:
            raise ValueError("user_query must be a dict for HumanEval.")
        
        response = self.llm.generate_response(self.VANILLA_PROMPT + user_query["prompt"], 
                                              suppress_conversation_history = suppress_conversation_history)
        
        # Parsing
        requirements, code, _ = parse_codellama(response) # not usign the example code for now.
        
        self._create_main_py(code, user_query)
        
        # Create requirements.txt
        self._create_requirements_txt(requirements) # TODO: deactivated for now.