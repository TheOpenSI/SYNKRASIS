import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess
from subprocess import CompletedProcess

from services.Base import ServiceBase
from services.Container.Container import Container
from services.Ollama.Ollama import Ollama
from utils.code_parsing.code_parser import parse_codellama
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_pycapsule, print_model_output

class PyCapsule(ServiceBase):
    def __init__(self, 
                 pycapsule_container: Container,
                 llm: Ollama,
                 maximum_attempts: int = 3):
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


    def _change_system_prompt(self, is_fix_mode: bool = False):
        """
        Change the system promopt for code generation.
        Reads the prompt from a file.
        """
        if not is_fix_mode:
            prompt_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_gen_prompt.txt")
        else:
            prompt_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_fix_prompt.txt")
            
        with open(prompt_file_path, "r") as file:
            code_gen_prompt = file.read().strip()
        self.llm.set_system_prompt(code_gen_prompt)


    def _generate_code(self, user_query: str, suppress_conversation_history: bool = True):
        """
        Uses the Ollama object to generate code.
        Create main.py and requirements.txt files in the mount_dir.
        Args:
            user_query (str): User query to generate code.
        """
        response = self.llm.generate_response(user_query, 
                                              suppress_conversation_history = suppress_conversation_history)
        print_model_output(response, self.llm.model)
        requirements, code, example = parse_codellama(response)
        
        mount_dir = os.path.abspath(__file__).replace("PyCapsule.py", "../Container/mount_dir")
        
        # Time complexity
        example = ("import time\n"
                   "start_time = time.time()\n"
                   f"{example}\n"
                   "end_time = time.time()\n"
                   "print(f'Execution time: {end_time - start_time} seconds')")
        
        # Create main.py
        with open(os.path.join(mount_dir, "main.py"), "w") as file:
            file.write(code + '\n\n' + example)
        
        # Create requirements.txt
        if not(len(requirements) == 1 and "none" in requirements):
            with open(os.path.join(mount_dir, "requirements.txt"), "w") as file:
                file.write('\n'.join(requirements))
            
            
    def _fix_code(self, response: CompletedProcess):
        """
        Gets activated only when response.returncode != 0.
        Will change sytem prompt and attempt to fix the code.

        Args:
            response (CompletedProcess): Response from the container with error code, stdout and stderr.
        """
        print_pycapsule("Starting PyCapsule in fix mode.")
        attempt_count = 0
        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode=True) # Will chnage the system prompt and reset the chat history
            fix_mode_query = ("Your generated code had the following error -\n"
                              f"{response.stderr}\n") # TODO: Consider adding the code and example here
            
            # Updating response, main.py and requirements.txt
            self._generate_code(fix_mode_query, suppress_conversation_history = False)
            
            # Running the code
            response = self.container.start_container()
            attempt_count += 1
        self._change_system_prompt() # Resetting the system prompt
        
    
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
        
    def __call__(self, user_query: str):
        # This will generate response from LLM and parse the response to get the code
        self.llm._set_seed()
        self._generate_code(user_query)
        
        # Start the container
        response: CompletedProcess = self.container.start_container()
        if response.returncode != 0:
            print_error("Generated code returned a non-zero exit code. Starting pycapsule in fix mode.")
            self.llm._set_seed()
            self._fix_code(response)
            

        
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