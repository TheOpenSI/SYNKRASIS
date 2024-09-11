import os
import sys
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"


from services.LLM.LLM import LLM
from services.Embedding.Embedding import EmbeddingModel
from services.VectorDatabase.VectorDatabase import VectorDatabase
from services.RAG.RAG import RAG
from services.Ollama.Ollama import Ollama
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))

def main():
    # All services
    llm: LLM = None
    embedding_model: EmbeddingModel = None
    vector_db: VectorDatabase = None
    ollama: Ollama = None
    rag: RAG = None
    
    try:
        embedding_model = EmbeddingModel()
        vector_db = VectorDatabase(embedding_model = embedding_model, chunk_size=200)
        ollama = Ollama()
        rag = RAG(vector_db = vector_db, llm = ollama)
        
        rag_response = rag.query("Who is the author of Disqualified?")
        print_model_output(rag_response, ollama.model)

    finally:
      # warning resource_tracker: There appear to be .* leaked semaphore objects"
      call_cleanup([llm, embedding_model, vector_db, ollama, rag])

if __name__ == '__main__':
    main()
