# =======================================================================================
# To add conversation history, set enable_chat_history=True in the Ollama object.
# In self.generate_response(), change suppress_conversation_history to False, 
# to include conversation history.
# May disable model pulling, have to do this manually
# Usage:
#     - generate_response(user_prompt: str, 
#                         context: List[str] = None, 
#                         suppress_conversation_history: bool = True) -> Optional[str]
#     - cleanup():
# https://ollama.com/blog/ollama-is-now-available-as-an-official-docker-image
# https://github.com/ollama/ollama/issues/1829
# Customise: https://github.com/ollama/ollama
# =======================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import requests, subprocess
from typing import Optional, Dict, List

from services.LLM.Ollama.Ollama import Ollama
from utils.output_message_format.output_colour import print_error, print_info
from utils.output_message_format.output_colour import print_success, print_model_output
from utils.code_parsing.code_parser import parse_response
from utils.spinner.Spinner import Spinner


class OllamaContainer(Ollama):
    def __init__(self, 
                 model_name: str = "mistral", # uses mistral as default model
                 enable_chat_history:bool = False, 
                 max_history: int = 3,
                 verbose_switch: bool = False,
                 container_name = "ollama"):
        """
        Ollama container class for running ollama from the official Ollama container.

        Args:
            model_name (str, optional): Name of the model to use. Defaults to "mistral".
            max_history (int, optional): Maximum chat history to keep. Defaults to 3.
            verbose_switch (bool, optional): Whether to print the full query being sent to 
                the model. Defaults to False.
            container_name (str, optional): Name of the ollama container. 
                Defaults to "ollama".
        """
        super().__init__(model_name, enable_chat_history, max_history, verbose_switch)
        self.container_name = container_name
        self.spinner = Spinner(message="Pulling Model..")
    
    
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
        self.spinner.start()          
        pull_command = f"docker exec -it {self.container_name} ollama pull {self.model_name}"
        subprocess.run(pull_command, shell=True)
        self.spinner.stop()
        print_success(f"Model {self.model_name} pulled successfully.")

            
    def check_model_availability(self):
        """
        Check if the model is available on the ollama server.
        """
        available_models = self._get_model_list()
        if self.model_name in available_models:
            print_info((f"{self.model_name} already exists on the ollama server. "
                        "Starting the model..."))
        else:
            self._pull_model()

    # def generate_response(self,
    #                       user_prompt: str,
    #                       context: List[str] = None,
    #                       suppress_conversation_history: bool = True) -> Optional[str]:
    #     """
    #     Generate a response from the user query using the model, including chat history.
    #     Args:
    #         user_prompt (str): The user query
    #         context (str): optional context
    #         suppress_conversation_history (bool): Whether to send conversation history.
    #     """
    #     # Conversation history
    #     conversation_history = ("" 
    #                             if suppress_conversation_history 
    #                             else self._prepare_conversation_history(user_prompt))

    #     # Context
    #     context = self._prepare_context(context)

    #     # Generate the prompt from message list
    #     # Keep the sequence of messages as follows: System, Context, Conversation, User
    #     messages = [{"role": "System", "content": self.system_prompt},
    #                 {"role": "Conversation", "content": conversation_history},
    #                 {"role": "Context", "content": context},
    #                 {"role": "User", "content": user_prompt}]
    #     full_query = self._prepare_prompt(messages) # bos_token is empty by default, applies default jinja template
        
    #     try:
    #         # Generate response from the model
    #         response = ollama.generate(model = self.model_name, prompt = full_query)

    #         # Add the interaction to chat history
    #         if self.enable_chat_history and response:
    #             if not self.chat_history:
    #                 self.init_chat_history(user_prompt)

    #             # self.chat_history.add_interaction(user_prompt,
    #             #                                   response["response"])  # for chat it's response["message"]["content"]
    #             # TODO: Make this accessible from other servcices, e.g. pycapsule
    #             _, code = parse_response(response["response"])
    #             self.chat_history.add_interaction(user_prompt, code)
                
    #         if self.verbose_switch:
    #             print_model_output(full_query, "USER")
    #             print()
                
    #         print_model_output(response["response"], self.model_name)
    #         return response["response"]

    #     except ollama.ResponseError as e:
    #         print_error(f"Caught ollama._types.ResponseError: {e}")
    #         print_info("Attempting to pull the model, please restart the service once pull is complete.")
    #         print_info("This may take a few minutes.")
    #         print_info("No output will be visible at stdout until the model is pulled.")
    #         self._pull_model()
    #         print_success("Model pull complete. Please restart the service.")
        
        
    def cleanup(self):
        """
        Nothing to clean up for Ollama
        """
        print_success("Ollama resources cleaned up.")