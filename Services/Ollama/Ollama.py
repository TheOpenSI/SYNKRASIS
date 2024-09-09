import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import ollama
from typing import Optional, Dict, List
from jinja2 import Template

from Services.Base import ServiceBase
from utils.output_message_format.output_colour import print_error, print_info
from modules.ChatHistory import ChatHistory

class Ollama(ServiceBase):
    def __init__(self, model: str = "mistral", enable_chat_history:bool = False):  # uses mistral as default model
        super().__init__()
        self.prompt_template_path = os.path.abspath(__file__).replace("Ollama.py", 
                                                                      "../../config_files/default_chat_template.jinja")
        self.model = model
        self.system_prompt = "Always answer the question to the best of your ability even if the context is not useful."
        self.enable_chat_history = enable_chat_history
        self.chat_history: ChatHistory = None


    def _pull_model(self):
        """
        Pull the model from the server
        """
        ollama.pull_model(self.model)


    def _init_chat_history(self, original_question: str, max_history: int = 3):
        """
        Initialize the chat history with the original question.
        Args:
            original_question (str): The initial question to start the chat.
            max_history (int): Maximum number of interactions to store in history.
        """
        self.chat_history = ChatHistory(original_question, max_history)


    def _generate_prompt(self, messages: List[Dict], bos_token=""):
        """
        Generate a prompt from the provided messages using the template.
        Args:
            messages (List[str]): List of messages to include in the prompt.
            bos_token (str): The BOS token to use in the prompt.
        """
        filtered_messages = [msg for msg in messages if msg.get("content").strip()]
        with open(self.prompt_template_path, "r") as jinja_file:
            template_str = jinja_file.read()

        # Create a Jinja template object
        template = Template(template_str)

        # Render the template with the provided messages and bos_token
        rendered_prompt = template.render(messages = filtered_messages, bos_token = bos_token)

        return rendered_prompt


    def generate_response(self, user_query: str, context:str = "") -> Optional[str]:
        """
        Generate a response from the user query using the model, including chat history.
        Args:
            user_query (str): The user query
        """
        try:
            conversation_history = "" # no conversation history by default
            if self.enable_chat_history:
                if self.chat_history is None:
                    self._init_chat_history(user_query) # user_query is the original question and max_history is 3 by default

                    # Prepare the context from chat history
                conversation_history = "\n" + "\n".join([(f"\tPrevious Qestion {index + 1}: {q}\n"
                                            f"\tPrevious Answer {index + 1}: {a}\n") 
                                            for index, (q, a) in enumerate(self.chat_history.conversation_history)])
            
            # Prepare the messages to generate the prompt
            # Keep the sequece of messages as follows: System, Context, Conversation, User
            messages = [{"role": "System", "content": self.system_prompt},
                        {"role": "Context", "content": context},
                        {"role": "Conversation", "content": conversation_history},
                        {"role": "User", "content": user_query}]
            full_query = self._generate_prompt(messages) # bos_token is empty by default

            # Generate response from the model
            response = ollama.generate(model = self.model, prompt = full_query)

            # Add the interaction to chat history
            if self.enable_chat_history and self.chat_history and response:
                self.chat_history.add_interaction(user_query, response["response"]) # for chat it's response["message"]["content"]

            return response["response"]

        except ollama.ResponseError as e:
            print_error(e.error)
            if e.status_code == 404:
                print_info("Attempting to pull the model")
                self._pull_model()


    def set_system_prompt(self, prompt: str):
        """
        Set the system prompt and reset the chat history.
        Args:
            prompt (str): The system prompt
        """
        self.system_prompt = prompt
        if self.enable_chat_history:
            self.chat_history = None  # reset chat history when system prompt changes
        
        
    def cleanup(self):
        """
        Nothing to cleanup for Ollama
        """
        pass