import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from typing import Union, Optional, List
from pathlib import Path

from services.Base import ServiceBase
from services.VectorDatabase.VectorDatabase import VectorDatabase
from services.LLM.LLMBase import LLMBase
from services.LLM.HF_LLM.HF_LLM import HF_LLM
from services.LLM.Ollama.Ollama import Ollama
from utils.output_message_format.output_colour import print_error, print_info, print_success

class RAG(ServiceBase):
    def __init__(self, 
                 vector_db: VectorDatabase, 
                 llm: LLMBase):
        """
        Initialize the RAG service, Requires LLM or Ollama and VectorDatabase to be initialized
        Args:
            vector_db (VectorDatabase): The vector database to use
            llm (LLMBase): The language model to use, can be HF_LLM or Ollama
        """
        super().__init__()
        self.vector_db = vector_db
        self.llm = llm
        
        
    def add_documents(self, file_paths: Union[str, Path, List[Union[str, Path]]]) -> None:
        """
        Add documents to the vector database by chunking them and generating embeddings.
        Args:
            file_paths (Union[str, Path, List[Union[str, Path]]]): A single file path or a list of file paths to add to the vector database.
        """
        self.vector_db.add_documents(file_paths)
        

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