import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from Services.Base import ServiceBase
from Services.VectorDatabase.VectorDatabase import VectorDatabase
from Services.LLM.LLM import LLM


class RAG(ServiceBase):
    def __init__(self, 
                 vector_db: VectorDatabase, # will have an embedding model
                 llm: LLM
                 ):
        """
        Initialize the RAG service, Requires LLM and VectorDatabase to be initialized
        Args:
            embedding_model (EmbeddingModel): The embedding model to use
            vector_db (VectorDatabase): The vector database to use
            llm (LLM): The LLM model to use
        """
        super().__init__()
        self.vector_db = vector_db
        self.llm = llm

        self.system_prompt = self.set_system_prompt()
        # Changing the system prompt for RAG
        self.llm.set_system_prompt(self.system_prompt)

    def set_system_prompt(self, system_prompt: str = None) -> str:
        if system_prompt is None:
            system_prompt = "You are a document search assistant. Answer the following question based on the provided context only."
        return system_prompt


    def query(self, user_query: str) -> str:
        context = self.vector_db.query(user_query)
        response = self.llm.generate_response(user_query, context)
        return response