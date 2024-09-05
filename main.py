import os
import sys
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"


from Services.LLM.LLM import LLM
from Services.Embedding.Embedding import EmbeddingModel
from Services.VectorDatabase.VectorDatabase import VectorDatabase
from utils.output_message_format.output_colour import print_model_output, print_info

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))

def main():
    llm: LLM = None
    embedding_model: EmbeddingModel = None
    vector_db: VectorDatabase = None
    
    try:
  
        # llm = LLM(llm_config_file=LLM_CONFIG_FILE)
        embedding_model = EmbeddingModel() # can reuse
        vector_db = VectorDatabase(embedding_model = embedding_model, chunk_size=200)
        
        # llm_response = llm.generate_response("Write a python function that can multiply 2 matrices.")
        # print_model_output(llm_response, llm.repo_name)

        result = vector_db.query("Who is the author of the book Disqualified?")
        print_info(f"[FETCHED] {result}")
        
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

        import gc
        gc.collect()


if __name__ == '__main__':
    main()
    time.sleep(20)
