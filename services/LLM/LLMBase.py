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
#   - _prepare_conversation_history(user_query: str) -> str @deprecated
#   - _prepare_system_prompt(suppress_conversation_history: bool = True) -> str
#   - _prepare_messages(user_prompt: str, context: List[str] = None,
#                       suppress_conversation_history: bool = True) -> List[Dict[str, str]]
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

from deprecated import deprecated
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
                 verbose_switch: bool = False):
        """
        Base class for all LLM services
        Args:
            model_name (str): Model name as string, use for printing and logging
            enable_chat_history (bool, optional): Use chat history. Defaults to False.
            max_history (int, optional): Maximum number of interactions to store in history. 
                Defaults to 3.
            verbose_switch (bool, optional): Whether to print out full prompt and response. 
                Defaults to False.
        """
        super().__init__()
        self.model_name = model_name
        self.prompt_template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "../../config_files/default_chat_template.jinja")
        self.enable_chat_history = enable_chat_history
        self.chat_history: ChatHistory = None
        self.max_history = max_history
        self.verbose_switch = verbose_switch
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
            context_str = "\n".join([f"- {ctx}" for ctx in context])

        return context_str


    @deprecated(reason="Use _prepare_messages instead", action="always")
    def _prepare_conversation_history(self, user_query: str) -> str:
        """
        Prepares a flat conversation history string context from chat history if 
            enable_chat_history is activated.

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
    
    
    def _prepare_system_prompt(self, suppress_conversation_history: bool = True) -> str:
        """
        Prepare the system prompt. Once there are previous turns, the original question is
        appended in a tag, so it is always present regardless of how much history is trimmed.

        Args:
            suppress_conversation_history (bool, optional): Skip the original question tag.
                Defaults to True.

        Returns:
            str: system prompt
        """
        system_prompt = self.system_prompt
        if (
            self.enable_chat_history 
            and not suppress_conversation_history
            and self.chat_history is not None
            and self.chat_history.history_length > 0
        ):
            system_prompt += (f"\n\n<original_question>\n{self.chat_history.original_question}\n"
                              "</original_question>")
        return system_prompt


    def _prepare_messages(self,
                          user_prompt: str,
                          context: List[str] = None,
                          suppress_conversation_history: bool = True) -> List[Dict[str, str]]:
        """
        Prepare the conversation as alternating user/assistant turns, ending with the current user turn.
        The system prompt is not included, use _prepare_system_prompt() and pass it the way the
        backend expects.
        Context is attached only to the current turn and is never stored in the chat history.

        Args:
            user_prompt (str): user query
            context (List[str], optional): RAG context. Defaults to None.
            suppress_conversation_history (bool, optional): Skip previous turns. Defaults to True.

        Returns:
            List[Dict[str, str]]: messages with roles "user" and "assistant"
        """
        messages = []
        if self.enable_chat_history and not suppress_conversation_history:
            # Initialise chat history if not already initialised
            if self.chat_history is None:
                self.init_chat_history(user_prompt)

            for question, answer in self.chat_history.conversation_history:
                # Roles must alternate, skip incomplete pairs
                if question.strip() and answer.strip():
                    messages.append({"role": "user", "content": question})
                    messages.append({"role": "assistant", "content": answer})

        context_str = self._prepare_context(context)
        current_turn = (
            f"<context>\n{context_str}\n</context>\n\n{user_prompt}"
            if context_str 
            else user_prompt
        )
        messages.append({"role": "user", "content": current_turn})
        return messages


    def get_messages_as_string(self, 
                               system_prompt: str, 
                               messages: List[Dict[str, str]]) -> str:
        """
        Get the messages as a single string for printing or logging.

        Args:
            system_prompt (str): The system prompt
            messages (List[Dict[str, str]]): List of messages with roles "user" and "assistant"
        
        Returns:
            str: The messages as a single string
        """
        return system_prompt + "\n\n" + "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages) + "\n"


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