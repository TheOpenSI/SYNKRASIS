# =======================================================================================
# Replacement for Ollama Container.
# Uses the ollama client to interact with the Ollama server.
# Usage:
#     - generate_response(user_prompt: str, 
#                         context: List[str] = None, 
#                         suppress_conversation_history: bool = True) -> Optional[str]
#     - cleanup():
# see: https://docs.ollama.com/api/chat#body-stream
# see: https://docs.ollama.com/api-reference/show-model-details
# =======================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import ollama
from typing import Optional, Dict, List, Union
from ollama import Client

from services.LLM.LLMBase import LLMBase
from services.LLM.Ollama.OllamaPullManager import OllamaPullManager
from utils.output_message_format.output_colour import print_error, print_info
from utils.output_message_format.output_colour import print_success, print_model_output


class OllamaClient(LLMBase):
    def __init__(self, 
                 model_name: str = "mistral", # uses mistral as default model
                 enable_chat_history: bool = False, 
                 max_history: int = 3,
                 verbose_switch: bool = False,
                 container_name = "localhost",
                 local_port: int = 11434,
                 stream: bool = True,
                 think: Union[bool, str, None] = None,
                 keep_alive: Union[str, int] = "2m",
                 format: Union[str, object] = None,
                 logprobs: bool = False,
                 top_logprobs: int = 5,
                 use_default_options: bool = False,
                 options: dict = {}):
        """
        Initialise the OllamaClient, can be used using Ollama container.
        
        Args:
            model_name (str): The name of the model to use.
            enable_chat_history (bool): Whether to enable chat history.
            max_history (int): The maximum number of interactions to keep in chat history.
            verbose_switch (bool): Whether to print verbose output that indcludes system
                prompt, context, conversation history and user prompt.
            container_name (str): The name of the Ollama container.
            local_port (int): The port of the Ollama container.
            stream (bool): Whether to stream the response from the model.
            think (Union[bool, str, None]): Whether to use the model's think feature,
                Null uses the default value.
            keep_alive (Union[str, int]): Model keep-alive duration 
                (for example 5m or 0 to unload immediately)
            format (Union[str, object]): The format of the response from the model. Use 
                "json" or JSONSchema with Pydantic model.
            use_default_options (bool): Whether to use the default options for the model.
            options (dict): The options to use for the model.
        """
        super().__init__(model_name, enable_chat_history, max_history, verbose_switch)
        self.stream = stream
        self.think = think
        self.keep_alive = keep_alive
        self.options = options if options else self._get_def_options() \
            if use_default_options else {}
        self.format = format
        self.logprobs = logprobs # do not use for generation, only for debugging
        self.top_logprobs = top_logprobs # do not use for generation, only for debugging

        self._tag_model() # tag the model to support model availability check
        self.ollama_client = self._set_local_client(container_name, local_port)
        self.pull_manager = OllamaPullManager(model_name=self.model_name,
                                              mode="stochastic",
                                              interventions=[85, 95],
                                              max_retries= 3,
                                              fall_back_interval=60,
                                              ollama_client=self.ollama_client)
        self._pull_model()
        
        
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


    def _get_def_options(self) -> dict:
        return {
            "seed": 42, # integer
            "temperature": 0.7, # float
            "top_k": None, # integer, Limits next token selection to the K most likely
            "top_p": None, # float, Cumulative probability threshold for nucleus sampling
            "min_p": None, # float, Minimum probability threshold for token selection
            "stop": None, # str | list[str], Stop sequences that will halt generation
            "num_ctx": 4096, # integer, Context length size (number of tokens)
            "num_predict": None, # integer, Maximum number of tokens to generate
        }
        
        
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
        # Messages first, it initialises the chat history if needed
        messages = self._prepare_messages(user_prompt, context, suppress_conversation_history)
        system_prompt = self._prepare_system_prompt(suppress_conversation_history)

        # Generate response from the model
        response = self.ollama_client.chat(
            model = self.model_name,
            messages = [{"role": "system", "content": system_prompt}, *messages],
            format = self.format,
            stream = self.stream,
            think = self.think,
            keep_alive = self.keep_alive,
            options = self.options
        )
        answer = response["message"]["content"]

        # Add the interaction to chat history
        if self.enable_chat_history and response:
            if not self.chat_history:
                self.init_chat_history(user_prompt)

            self.chat_history.add_interaction(user_prompt, answer)
            
        if self.verbose_switch:
            print_model_output(self.get_messages_as_string(system_prompt, messages), "USER")
        
        if not answer:
            print_error("No response received from Ollama")
            return None
            
        print_model_output(answer + "\n", self.model_name)
        return answer
        
        
    def cleanup(self):
        """
        Nothing to clean up for Ollama
        """
        print_success("Ollama resources cleaned up.")


if __name__ == "__main__":
    # Example usage
    ollama_client = OllamaClient(model_name="qwen2.5:7b", 
                                 enable_chat_history=True, 
                                 verbose_switch=True,
                                 keep_alive="2m",
                                 use_default_options=True)
    response = ollama_client.generate_response("Hello, how are you?")
    print(response)