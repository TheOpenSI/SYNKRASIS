# =======================================================================================
# Ollama container class for running ollama from the official Ollama container.
# Ollama port is hard coded to 11434 for docker networking.
# Usage:
#     - generate_response(user_prompt: str, 
#                         context: List[str] = None, 
#                         suppress_conversation_history: bool = True) -> Optional[str]
#     - cleanup():
#
# Useful links:
#  - https://ollama.com/blog/ollama-is-now-available-as-an-official-docker-image
#  - https://github.com/ollama/ollama/issues/1829
#  - Customise: https://github.com/ollama/ollama
# =======================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import requests, subprocess
from typing import Optional, List

from services.LLM.LLMBase import LLMBase
from utils.output_message_format.output_colour import print_error, print_info
from utils.output_message_format.output_colour import print_success, print_model_output
from utils.code_parsing.code_parser import parse_response


class OllamaContainer(LLMBase):
    def __init__(self, 
                 model_name: str = "mistral", # uses mistral as default model
                 enable_chat_history:bool = False, 
                 max_history: int = 3,
                 verbose_switch: bool = False,
                 container_name = "ollama",
                 local_port: int = 11434):
        """
        Ollama container class for running ollama from the official Ollama container.

        Args:
            model_name (str, optional): Name of the model to use. Defaults to "mistral".
            max_history (int, optional): Maximum chat history to keep. Defaults to 3.
            verbose_switch (bool, optional): Whether to print the full query being sent to 
                the model. Defaults to False.
            container_name (str, optional): Name of the ollama container. 
                Defaults to "ollama".
            local_port (int, optional): Local port for the ollama container. Defaults to 11434.
        """
        super().__init__(model_name, enable_chat_history, max_history, verbose_switch)
        self.container_name = container_name
        self._check_model_availability()
        self.local_port = local_port
        self.api_url = f"http://{self.container_name}:{self.local_port}/api/generate"
    
    
    def _get_model_list(self) -> List[str]:
        """
        Get the list of models available on the ollama server.
        """
        shell_command = (f"docker exec -it {self.container_name} ollama list | "
                        f"awk '{{print $1}}'")
        
        get_model_list_process = subprocess.run(shell_command,
                                                shell=True,
                                                text=True,
                                                capture_output=True)
        available_models = [entry.strip().split(":")[0]
                            for entry in get_model_list_process.stdout.split("\n")
                            if entry != "" and entry != "NAME"]
        
        return available_models
            
        
    def _pull_model(self):
        """
        Pull the model from the server
        """
        print_info((f"{self.model_name} not found on the ollama server. "
                    "Pulling the model..."))     
        pull_command = f"docker exec -it {self.container_name} ollama pull {self.model_name}"
        subprocess.run(pull_command, shell=True)
        print_success(f"Model {self.model_name} pulled successfully.")

            
    def _check_model_availability(self):
        """
        Check if the model is available on the ollama server.
        """
        available_models = self._get_model_list()
        if self.model_name in available_models:
            print_info((f"{self.model_name} already exists on the ollama server. "
                        "Starting the model..."))
        else:
            self._pull_model()
            
            
    def _send_query(self, query: str) -> str:
        """
        Send user query to the ollama container.

        Args:
            query (str): User query.
        """
        payload = {
            "model": self.model_name,
            "prompt": query,
            "stream": False
        }
        response = requests.post(self.api_url, json=payload)
        return response.json()["response"]
            
        
    def generate_response(self,
                          user_prompt: str,
                          context: List[str] = None,
                          suppress_conversation_history: bool = True) -> Optional[str]:
        """
        Generate a response from the ollama container.
        Args:
            user_prompt (str): The user query
            context (str): optional context
            suppress_conversation_history (bool): Whether to send conversation history.
        """
        # Conversation history
        conversation_history = ("" 
                                if suppress_conversation_history 
                                else self._prepare_conversation_history(user_prompt))

        # Context
        context = self._prepare_context(context)

        # Generate the prompt from message list
        # Keep the sequence of messages as follows: System, Context, Conversation, User
        messages = [{"role": "System", "content": self.system_prompt},
                    {"role": "Conversation", "content": conversation_history},
                    {"role": "Context", "content": context},
                    {"role": "User", "content": user_prompt}]
        
        # bos_token is empty by default, applies default jinja template
        full_query = self._prepare_prompt(messages)
        
        try:
            # Generate response from the model
            response = self._send_query(full_query)

            # Add the interaction to chat history
            if self.enable_chat_history and response:
                if not self.chat_history:
                    self.init_chat_history(user_prompt)
                    
                # To add the whole response to chat history, add response without parsing.
                _, code = parse_response(response)
                self.chat_history.add_interaction(user_prompt, code)
                
            if self.verbose_switch:
                print_model_output(full_query, "USER")
                print()
                
            print_model_output(response, self.model_name)
            return response

        except ConnectionError as ce:
            print_error((f"Failed to connect to the ollama container. "
                         f"Make sure the ollama container is running at port {self.local_port}."))
            raise ce
        
        
    def cleanup(self):
        """
        Nothing to clean up for Ollama
        """
        # NOTE: We can stop the ollama container here if needed.
        print_success("Ollama resources cleaned up.")