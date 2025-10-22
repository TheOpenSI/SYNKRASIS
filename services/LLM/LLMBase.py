# ====================================================================================================================
# Usage -
# Fields:
#   - model_name: str
#   - prompt_template_path: str
#   - enable_chat_history: bool
#   - chat_history: ChatHistory
#   - system_prompt: str
#
# Methods:
#   - init_chat_history(original_question: str, max_history: int = 1)
#   - _prepare_prompt(messages: List[Dict], bos_token: str) -> str
#   - _prepare_context(context: List[str]) -> Optional[str]
#   - _prepare_conversation_history(user_query: str) -> str
#   - set_system_prompt(prompt: str)
#   - set_system_prompt_from_file(prompt_file: str = None)
#   - clear_chat_history()
#
# Abstract Methods:
#   - generate_response(user_prompt: str, context:List[str] = None, suppress_conversation_history:bool = True) 
#                                                                                               -> Optional[str]
# ====================================================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from abc import abstractmethod
from typing import List, Optional, Dict
from jinja2 import Template

from services.Base import ServiceBase
from modules.ChatHistory import ChatHistory
from utils.output_message_format.output_colour import print_error, print_success

class LLMBase(ServiceBase):
    def __init__(self, 
                 model_name: str, 
                 enable_chat_history: bool = False,
                 max_history: int = 3,
                 verbose_switch: bool = False,
                 suppress_stdout: bool = False):
        """
        Base class for all LLM services
        Args:
            model_name (str): Model name as string, use for printing and logging
            enable_chat_history (bool, optional): Use chat history. Defaults to False.
            max_history (int, optional): Maximum number of interactions to store in history. 
                Defaults to 3.
            verbose_switch (bool, optional): Whether to print out full prompt and response. 
                Defaults to False.
            suppress_stdout (bool, optional): Whether to suppress stdout printing.
        """
        super().__init__()
        self.model_name = model_name
        self.prompt_template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "../../config_files/default_chat_template.jinja")
        self.enable_chat_history = enable_chat_history
        self.chat_history: ChatHistory = None
        self.max_history = max_history
        self.verbose_switch = verbose_switch
        self.suppress_stdout = suppress_stdout
        self.system_prompt = ("You are a helpful assistant, "
                              "always answer the question to the best of your ability "
                              "even if the context is not useful.")


    def _prepare_prompt(self, messages: List[Dict], bos_token="") -> str:
        """
        Using the default jinja template, generate a prompt from the provided message list and role.
        Args:
            messages (List[str]): List of messages to include in the prompt.
            bos_token (str): The BOS token to use in the prompt.
        """
        filtered_messages = [msg for msg in messages if msg.get("content").strip()]  # Filter out empty messages.

        with open(self.prompt_template_path, "r") as jinja_file:
            template_str = jinja_file.read()

        # Create a Jinja template object
        template = Template(template_str)

        # Render the template with the provided messages and bos_token
        rendered_prompt = template.render(messages=filtered_messages, bos_token=bos_token)
        return rendered_prompt


    def _prepare_context(self, context: List[str]) -> Optional[str]:
        """
        Prepare context for the prompt if context is provided.
        Args:
            context (List[str]): List of context strings
        """
        context_str = ""
        if context:
            context_str = "\n".join([f"\t{ctx}" for ctx in context])

        return context_str

        
    def _prepare_conversation_history(self, user_query: str) -> str:
        """
        Prepare conversation history context from chat history if enable_chat_history is activated.

        Args:
            user_query (str): user query, only used if chat history is not initialised
            
        Returns:
            str: conversation history context
        """
        conversation_history = ""
        if self.enable_chat_history:
            
            # Initialise chat history if not already initialised
            if self.chat_history is None:
                self.init_chat_history(user_query) 
            
            # Original question
            conversation_history = ">> Original Question: " + self.chat_history.original_question + "\n"
            
            # Uncomment to pass only the original question and last answer
            # conversation_history += "\n".join([(f">> Your previous answer:\n{answer}\n") 
                                            #    for _, answer in self.chat_history.conversation_history])
            
            # Passing both question and answer
            for i, (question, answer) in enumerate(self.chat_history.conversation_history):
                # Skip the first question since it's same as the original question
                if question != self.chat_history.original_question:
                    conversation_history += f">> Previous question {i+1}: {question}\n"
                # conversation_history += f">> Your previous solution {i+1}:\n{code}\n\n" # Uncomment for pycapsule
                conversation_history += f">> Your previous response {i+1}: {answer}\n\n"
            
            return conversation_history
    
    
    def init_chat_history(self, original_question: str):
        """
        Initialize the chat history with the original question, only call if enable_chat_history is set to True.
        Args:
            original_question (str): The initial question to start the chat.
        """
        if not self.enable_chat_history:
            print_error("Chat history is not enabled.")
            return
        self.chat_history = ChatHistory(original_question, self.max_history)
        

    def set_system_prompt(self, prompt: str):
        """
        Set the system prompt and reset the chat history.
        Args:
            prompt (str): The system prompt
        """
        self.system_prompt = prompt
        # NOTE: Consider clearing the chat history here.

        
    def clear_chat_history(self):
        """
        Clear the chat history, happens automatically when system prompt changes.
        """
        if self.enable_chat_history:
            self.chat_history = None
            print_success("Chat history cleared.")
        else:
            print_error("Chat history is not enabled.")

            
    def set_system_prompt_from_file(self, prompt_file: str = None):
        """
        Set the system prompt from a file.
        By default, it loads from config_files/system_prompt.txt.
        Args:
            prompt_file (str): The file containing the system prompt.
        """
        if prompt_file is None:
            prompt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "../../config_files/system_prompt.txt")
        with open(prompt_file, "r") as prompt_file:
            self.system_prompt = prompt_file.read()
        # NOTE: Consider clearing the chat history here.
    
   
    @abstractmethod
    def generate_response(self,
                          user_prompt: str,
                          context: List[str] = None,
                          suppress_conversation_history: bool = True) -> Optional[str]:
        """
        Generate a response using the LLM

        Args:
            user_prompt (str): User query
            context (List[str], optional): RAG context. Defaults to None.
            suppress_conversation_history (bool, optional): Add conversation history. Defaults to True.

        Returns:
            Optional[str]: LLM response
        """
        pass