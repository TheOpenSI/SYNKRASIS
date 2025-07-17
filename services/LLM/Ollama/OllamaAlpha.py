# =======================================================================================
# Replacement for Ollama Container.
# Used ollama client to interact with the Ollama server.
# Usage:
#     - generate_response(user_prompt: str, 
#                         context: List[str] = None, 
#                         suppress_conversation_history: bool = True) -> Optional[str]
#     - cleanup():
# =======================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import ollama, torch
from typing import Optional, Dict, List
from ollama import Client

from services.LLM.LLMBase import LLMBase
from services.LLM.Ollama.OllamaPullManager import OllamaPullManager
from utils.output_message_format.output_colour import print_error, print_info
from utils.output_message_format.output_colour import print_success, print_model_output


class Ollama(LLMBase):
    def __init__(self, 
                 model_name: str = "llama3.1", # uses mistral as default model
                 enable_chat_history:bool = False, 
                 max_history: int = 3,
                 verbose_switch: bool = False,
                 container_name = "ollama",
                 local_port: int = 11434):
        super().__init__(model_name, enable_chat_history, max_history, verbose_switch)
        self._tag_model() # tag the model to support model availability check
        self.pull_manager = OllamaPullManager(model_name=self.model_name,
                                              mode="stochastic",
                                              interventions=[85, 95],
                                              max_retries= 3,
                                              fall_back_interval=60)
        self._pull_model()
        self.ollama_client = self._set_local_client(container_name, local_port)
        
        
    def _set_local_client(self,
                          container_name: str,
                          port: int) -> Client:
        """
        Set the local client for the Ollama container.

        Args:
            container_name (str): Name of the Ollama container.
        """
        client = ollama.Client(
            host = f"http://{container_name}:{port}",
            headers = {"Content-Type": "application/json"}
        )
        return client
        
        
    def _tag_model(self) -> None:
        """
        Tag the model with latest if not already tagged.
        """
        if ":" not in self.model_name:
            self.model_name = f"{self.model_name}:latest"


    def _pull_model(self):
        """
        Pull the model from the server with progress tracking
        """
        self.pull_manager.pull_model()


    def generate_response(self,
                          user_prompt: str,
                          context: List[str] = None,
                          suppress_conversation_history: bool = True) -> Optional[str]:
        """
        Generate a response from the user query using the model, including chat history.
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
        
        # Generate response from the model
        response = self.ollama_client.generate(model = self.model_name, prompt = full_query)

        # Add the interaction to chat history
        if self.enable_chat_history and response:
            if not self.chat_history:
                self.init_chat_history(user_prompt)

            # For chat it's response["message"]["content"]
            self.chat_history.add_interaction(user_prompt,
                                                response["response"])  
            
        if self.verbose_switch:
            print_model_output(full_query, "USER")
            print("\n")
            
        print_model_output(response["response"], self.model_name)
        print("\n")
        return response["response"]
        
        
    def cleanup(self):
        """
        Nothing to clean up for Ollama
        """
        print_success("Ollama resources cleaned up.")