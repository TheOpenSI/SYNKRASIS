# To add conversation history, set enable_chat_history=True in the Ollama object.
# In self.generate_response(), change suppress_conversation_history to False to include conversation history.

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import ollama, torch
from typing import Optional, Dict, List

from services.Base import ServiceBase
from services.LLM.LLMBase import LLMBase
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_model_output

class Ollama(ServiceBase, LLMBase):
    def __init__(self, model_name: str = "mistral", enable_chat_history:bool = False):  # uses mistral as default model
        ServiceBase.__init__(self)
        LLMBase.__init__(self, model_name, enable_chat_history)
        
    def _set_seed(self):
        torch.manual_seed(42)
        torch.cuda.manual_seed_all(42)


    def _pull_model(self):
        """
        Pull the model from the server
        """
        ollama.pull_model(self.model_name)


    def generate_response(self, 
                          user_prompt: str, 
                          context:List[str] = None, 
                          suppress_conversation_history:bool = True) -> Optional[str]:
        """
        Generate a response from the user query using the model, including chat history.
        Args:
            user_prompt (str): The user query
        """
        # Conversation history
        conversation_history = "" if suppress_conversation_history else self._prepare_conversation_history(user_prompt)
        
        # Context
        context = self._prepare_context(context)
                
        # Generate the prompt from message list 
        # Keep the sequece of messages as follows: System, Context, Conversation, User
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
                    self._init_chat_history(user_prompt)
                    
                self.chat_history.add_interaction(user_prompt, response["response"]) # for chat it's response["message"]["content"]

            print_model_output(response["response"], self.model_name)
            return response["response"]

        except ollama.ResponseError as e:
            print_error(e.error)
            if e.status_code == 404:
                print_info("Attempting to pull the model, please restart the service once pull is complete.")
                self._pull_model()
        
        
    def cleanup(self):
        """
        Nothing to cleanup for Ollama
        """
        print_success("Ollama resources cleaned up.")