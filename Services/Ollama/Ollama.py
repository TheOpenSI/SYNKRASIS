import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import ollama
from typing import Optional, Dict 

from Services.Base import ServiceBase
from utils.output_message_format.output_colour import print_error, print_info
from modules.ChatHistory import ChatHistory

class Ollama(ServiceBase):
    def __init__(self,model: str = "mistral"):  # uses mistral as default model
        super().__init__()
        self.model = model
        self.system_prompt = "Always answer the question to the best of your ability even if the context is not useful."
        self.chat_history = None


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

    def generate_response(self, user_query: str) -> Optional[Dict]:
        """
        Generate a response from the user query using the model, including chat history.
        Args:
            user_query (str): The user query
        """
        try:
            if self.chat_history is None:
                self._init_chat_history(user_query)  # Initialize history if not already

            # Prepare the context from chat history
            history_context = "\n".join([f"Q: {q}\nA: {a}" for q, a in self.chat_history.conversation_history])
            context = f"Context:\n{history_context}\n" if history_context else ""

            # Append the user's current query to the context
            full_query = f"{context}Question: {user_query}"

            # Generate response from the model
            response = ollama.chat(self.model, messages=[{"role": "system", "content": self.system_prompt},
                                                    {"role": "user", "content": full_query}])

            # Add the interaction to chat history
            if response:
                self.chat_history.add_interaction(user_query, response["message"]["content"])

            return response["message"]["content"]

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
        self.chat_history = None  # reset chat history when system prompt changes
        
        
    def cleanup(self):
        """
        Nothing to cleanup for Ollama
        """
        pass