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
# =======================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import ollama, torch
from typing import Optional, Dict, List

from services.LLM.LLMBase import LLMBase
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_model_output
from utils.code_parsing.code_parser import parse_response


class Ollama(LLMBase):
    def __init__(self, 
                 model_name: str = "mistral", # uses mistral as default model
                 enable_chat_history:bool = False, 
                 max_history: int = 3,
                 verbose_switch: bool = False):
        # Init will not load the model in GPU, model gets loaded only when generate_response is called
        super().__init__(model_name, enable_chat_history, max_history, verbose_switch)
        
        
    def _set_seed(self):
        torch.manual_seed(42)
        torch.cuda.manual_seed_all(42)


    def _pull_model(self):
        """
        Pull the model from the server
        """
        ollama.pull(self.model_name)


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
        conversation_history = "" if suppress_conversation_history else self._prepare_conversation_history(user_prompt)

        # Context
        context = self._prepare_context(context)

        # Generate the prompt from message list
        # Keep the sequence of messages as follows: System, Context, Conversation, User
        messages = [{"role": "System", "content": self.system_prompt},
                    {"role": "Conversation", "content": conversation_history},
                    {"role": "Context", "content": context},
                    {"role": "User", "content": user_prompt}]
        full_query = self._prepare_prompt(messages) # bos_token is empty by default, applies default jinja template
        
        try:
            # Generate response from the model
            response = ollama.generate(model = self.model_name, prompt = full_query)

            # Add the interaction to chat history
            if self.enable_chat_history and response:
                if not self.chat_history:
                    self.init_chat_history(user_prompt)

                # self.chat_history.add_interaction(user_prompt,
                #                                   response["response"])  # for chat it's response["message"]["content"]
                # TODO: Make this accessible from other servcices, e.g. pycapsule
                _, code = parse_response(response["response"])
                self.chat_history.add_interaction(user_prompt, code)
                
            if self.verbose_switch:
                print_model_output(full_query, "USER")
                print()
                
            print_model_output(response["response"], self.model_name)
            return response["response"]

        except ollama.ResponseError as e:
            print_error(f"Caught ollama._types.ResponseError: {e}")
            print_info("Attempting to pull the model, please restart the service once pull is complete.")
            print_info("This may take a few minutes.")
            print_info("No output will be visible at stdout until the model is pulled.")
            self._pull_model()
            print_success("Model pull complete. Please restart the service.")
        
        
    def cleanup(self):
        """
        Nothing to clean up for Ollama
        """
        print_success("Ollama resources cleaned up.")