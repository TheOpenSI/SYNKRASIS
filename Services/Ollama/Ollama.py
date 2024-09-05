import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import ollama
from typing import Optional, Dict 

from Services.base import ServiceBase
from utils.output_message_format import print_error, print_info

class Ollama(ServiceBase):
    def __init__(self,
                 model:str = "mistral" # uses mistral as default model
                 ):
        super().__init__()
        self.model = ModuleNotFoundError
        self.system_prompt = "Always answer the question to the best of your ability even if the context is not useful."


    def _pull_model(self):
        """
        Pull the model from the server
        """
        ollama.pull_model(self.model)
    
    
    def set_system_prompt(self, prompt:str):
        """
        Set the system prompt
        Args:
            prompt (str): The system prompt
            default: "Always answer the question to the best of your ability even if the context is not useful."
        """
        self.system_prompt = prompt


    def generate_response(self, user_query:str) -> Optional[Dict]:
        """
        Generate a response from the user query using the model
        Args:
            user_query (str): The user query
        """
        try:
            response = ollama(self.model, messages=[{"role": "system", "content": self.system_prompt},
                                                    {"role": "user", "content": user_query}])
            return response

        except ollama.ResponseError as e:
            print_error(e.error)
            if e.status_code == 404:
                print_info("Attempting to pull the model")
                self._pull_model()
