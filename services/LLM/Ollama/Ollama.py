# =======================================================================================
# To add conversation history, set enable_chat_history=True in the Ollama object.
# In self.generate_response(), change suppress_conversation_history to False, 
# to include conversation history.
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

from services.LLM.LLMBase import LLMBase
from services.LLM.Ollama.OllamaPullManager import OllamaPullManager
from utils.output_message_format.output_colour import print_error, print_info
from utils.output_message_format.output_colour import print_success, print_model_output
from utils.code_parsing.code_parser import parse_response


class Ollama(LLMBase):
    def __init__(self, 
                 model_name: str = "llama3.1", # uses mistral as default model
                 enable_chat_history:bool = False, 
                 max_history: int = 3,
                 verbose_switch: bool = False):
        # Init won't load the model in GPU, model gets loaded only when generate_response is called
        super().__init__(model_name, enable_chat_history, max_history, verbose_switch)
        self._tag_model() # tag the model to support model availability check
        self.pull_manager = OllamaPullManager(model_name=self.model_name,
                                              mode="stochastic",
                                              interventions=[85, 95],
                                              max_retries= 3,
                                              fall_back_interval=60)
        self._pull_model()
        
        
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
        self.pull_manager._pull_model()


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
        
        try:
            # Generate response from the model
            response = ollama.generate(model = self.model_name, prompt = full_query)

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

        except ollama.ResponseError as e:
            print_error(f"Caught ollama._types.ResponseError: {e}")
            print_info("Attempting to pull the model again.")
            print_info("This may take a few minutes.")
            self._pull_model()
            # Retry the response generation after pulling the model
            return self.generate_response(user_prompt, 
                                          context, 
                                          suppress_conversation_history)
        
        
    def cleanup(self):
        """
        Nothing to clean up for Ollama
        """
        print_success("Ollama resources cleaned up.")