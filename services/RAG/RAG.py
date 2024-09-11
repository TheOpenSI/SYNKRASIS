import os
import sys
from typing import Union, Optional

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from services.Base import ServiceBase
from services.VectorDatabase.VectorDatabase import VectorDatabase
from services.LLM.LLM import LLM
from services.Ollama.Ollama import Ollama
from utils.output_message_format.output_colour import print_error, print_info, print_success

class RAG(ServiceBase):
    def __init__(self, vector_db: VectorDatabase, llm: Union[LLM, Ollama]):
        """
        Initialize the RAG service, Requires LLM or Ollama and VectorDatabase to be initialized
        Args:
            vector_db (VectorDatabase): The vector database to use
            llm (Union[LLM, Ollama]): The LLM or Ollama model to use
        """
        super().__init__()
        self.vector_db = vector_db  # vector db has the embedding model
        self.llm = llm # can be LLM or Ollama

        self.system_prompt = self.set_system_prompt() # RAG prompt
        
        # Changing the system prompt for RAG
        self.llm.set_system_prompt(self.system_prompt)

    def set_system_prompt(self, system_prompt: str = None) -> str:
        """
        Setting RAG system prompt
        Args:
            system_prompt (str, optional): If None, will use the default system prompt.

        Returns:
            str: The system prompt for RAG
        """
        if system_prompt is None:
            system_prompt = "You are a document search assistant. Answer the following question based on the provided context only."
        return system_prompt

    def query(self, user_query: str) -> Optional[str]:
        try:
            context = self.vector_db.query(user_query)
            response = self.llm.generate_response(user_query, context)
            
            if response is None:
                print_error("LLM returned None response")
                return "Couldn't generate a response at this time. Please try again later."
            
            return response

        except Exception as e:
            print_error(f"An error occurred during RAG query: {str(e)}")
            return "An error occurred while processing your query. Ollama will attempt to pull the model, try again later."

    def cleanup(self):
        """
        Cleanup method to handle any necessary cleanup for RAG components
        """
        try:
            self.vector_db.cleanup()
        except Exception as e:
            print_error(f"Error during vector_db cleanup: {str(e)}")

        try:
            self.llm.cleanup()
        except Exception as e:
            print_error(f"Error during llm cleanup: {str(e)}")
            
        print_success("RAG resources cleaned up.")