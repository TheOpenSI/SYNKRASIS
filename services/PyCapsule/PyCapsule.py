import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess

from services.Base import ServiceBase
from services.Container.Container import Container
from services.Ollama.Ollama import Ollama
from utils.code_parsing.code_parser import parse_input_improved
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_warning, print_model_output

class PyCapsule(ServiceBase):
    def __init__(self, 
                 pycapsule_container: Container,
                 llm: Ollama):
        super().__init__()
        if not llm.enable_chat_history:
            print_error("Chat history must be enabled in the LLM object for PyCapsule service")
            raise ValueError("Chat history must be enabled in the LLM object for PyCapsule service")
        self.container = pycapsule_container
        self.llm = llm
        self._change_system_prompt()


    def _change_system_prompt(self):
        prompt_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_gen_prompt.txt")
        with open(prompt_file_path, "r") as file:
            code_gen_prompt = file.read().strip()
        self.llm.set_system_prompt(code_gen_prompt)


    def _generate_code(self, user_query: str):
        response = self.llm.generate_response(user_query)
        print_model_output(response, self.llm.model)
        requirements, code, example = parse_input_improved(response)
        
        mount_dir = os.path.abspath(__file__).replace("PyCapsule.py", "../Container/mount_dir")
        
        # Create main.py
        with open(os.path.join(mount_dir, "main.py"), "w") as file:
            file.write(code + '\n\n' + example)
        
        # Create requirements.txt
        with open(os.path.join(mount_dir, "requirements.txt"), "w") as file:
            file.write('\n'.join(requirements))
        
        
    def validate_code(self, user_query: str):
        # This will generate response from LLM and parse the response to get the code
        self._generate_code(user_query)
        
        # Start the container
        self.container.start_container()

        
    # For testing only
    @staticmethod
    def run_command(command: str = "whoami") -> str:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()


    def cleanup(self):
        self.container.cleanup()
        self.llm.clear_chat_history()
        
        mount_dir = os.path.abspath(__file__).replace("PyCapsule.py", "../Container/mount_dir")
        for file in ['main.py', 'requirements.txt']:
            file_path = os.path.join(mount_dir, file)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        print_success("PyCapsule resources cleaned up.")