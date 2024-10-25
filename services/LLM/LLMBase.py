import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from jinja2 import Template

from modules.ChatHistory import ChatHistory
from utils.output_message_format.output_colour import print_error, print_success

class LLMBase(ABC):
    def __init__(self, enable_chat_history: bool = False):
        self.prompt_template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../config_files/default_chat_template.jinja")
        self.enable_chat_history = enable_chat_history
        self.chat_history: ChatHistory = None
        self.system_prompt = "Always answer the question to the best of your ability even if the context is not useful."
    
  
    def _generate_prompt(self, messages: List[Dict], bos_token="") -> str:
        """
        Generate a prompt from the provided messages using the default jinja template.
        Args:
            messages (List[str]): List of messages to include in the prompt.
            bos_token (str): The BOS token to use in the prompt.
        """
        filtered_messages = [msg for msg in messages if msg.get("content").strip()] # Filter out empty messages.
        with open(self.prompt_template_path, "r") as jinja_file:
            template_str = jinja_file.read()

        # Create a Jinja template object
        template = Template(template_str)

        # Render the template with the provided messages and bos_token
        rendered_prompt = template.render(messages = filtered_messages, bos_token = bos_token)

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


    def _init_chat_history(self, original_question: str, max_history: int = 1):
        """
        Initialize the chat history with the original question, only call if enable_chat_history is set to True.
        Args:
            original_question (str): The initial question to start the chat.
            max_history (int): Maximum number of interactions to store in history.
        """
        self.chat_history = ChatHistory(original_question, max_history)

    
    def _prepare_conversation_history(self, user_query: str, num_retrieved_history: int=1) -> str:
        """
        Prepare conversation histoy context from chat history if enable_chat_history is activated.

        Args:
            user_query (str): user query

        Returns:
            str: conversation history context
        """
        conversation_history = ""
        if self.enable_chat_history:
            if self.chat_history is None:
                self._init_chat_history(user_query) # user_query is the original question and max_history is 1 by default

            # Prepare the conversation history context from chat history
            conversation_history = "\n" + "Original Question: " + self.chat_history.original_question + "\n"
            conversation_history += "\n".join([(f"\tPrevious Question {index + 1}: {q}\n"
                                        f"\tPrevious Answer {index + 1}: {a}\n") 
                                        for index, (q, a) in enumerate(self.chat_history.conversation_history[-num_retrieved_history:])])
        
        return conversation_history
            
            
    def set_system_prompt(self, prompt: str):
        """
        Set the system prompt and reset the chat history.
        Args:
            prompt (str): The system prompt
        """
        self.system_prompt = prompt
        # TODO: Consider clearing the chat history here.
        
        
    def clear_chat_history(self):
        """
        Clear the chat history, happens automatically when system prompt changes.
        """
        if self.enable_chat_history:
            self.chat_history = None
            print_success("Chat history cleared.")
        else:
            print_error("Chat history is not enabled.")
    
    
    @abstractmethod
    def generate_response(self, 
                          user_prompt: str,
                          context:List[str] = None,
                          suppress_conversation_history:bool = True) -> Optional[str]:
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