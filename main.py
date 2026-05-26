import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Ollama.Ollama import Ollama
from services.LLM.Ollama.OllamaContainer import OllamaContainer
from services.Container.Container import Container
from services.Embedding.Embedding import EmbeddingModel
from services.RAG.RAG import RAG
from services.VectorDatabase.VectorDatabase import VectorDatabase

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error 
from utils.output_message_format.output_colour import print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from utils.ascii.synkrasis import print_synkrasis_logo


def main():
    print_synkrasis_logo()
    try:
        llm = Ollama(model_name = "qwen2.5-coder:7b", 
                     verbose_switch=True)
        embedding_model = EmbeddingModel()
        vector_db = VectorDatabase(embedding_model=embedding_model)
        rag = RAG(vector_db=vector_db, llm=llm)
        rag.add_documents(["Academic Governance Handbook 2025.pdf"])
        
        while True:
            query = input("Enter your query (or 'exit' to quit): ")
            if query.lower() == 'exit':
                break
            rag.query(query)

        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([rag])

if __name__ == '__main__':
    main()