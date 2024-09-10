import os
import sys
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"


from Services.LLM.LLM import LLM
from Services.Embedding.Embedding import EmbeddingModel
from Services.VectorDatabase.VectorDatabase import VectorDatabase
from Services.RAG.RAG import RAG
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))

def main():
    llm: LLM = None
    embedding_model: EmbeddingModel = None
    vector_db: VectorDatabase = None
    
    try:
        embedding_model = EmbeddingModel() # can reuse
        vector_db = VectorDatabase(embedding_model = embedding_model, chunk_size=200)

    finally:
      # warning resource_tracker: There appear to be .* leaked semaphore objects"
        if vector_db:
            vector_db.cleanup()
            del vector_db
        if embedding_model:
            embedding_model.cleanup()
            del embedding_model
        if llm is not None:
            llm.cleanup()
            del llm

if __name__ == '__main__':
    main()
    time.sleep(20)
