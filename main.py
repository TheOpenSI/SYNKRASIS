import os
import sys
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from services.Base import ServiceBase
from services.LLM.LLM import LLM
from services.Embedding.Embedding import EmbeddingModel
from services.VectorDatabase.VectorDatabase import VectorDatabase
from services.RAG.RAG import RAG
from services.Ollama.Ollama import Ollama
from services.Container.Container import Container
# from services.PyCapsule.PyCapsule import PyCapsule
from services.PyCapsule.PyCapsule_HumanEval import PyCapsule_HumanEval
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from data.HumanEval import HumanEvalDataset

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))

def main():
    # All services
    llm: LLM = None
    embedding_model: EmbeddingModel = None
    vector_db: VectorDatabase = None
    ollama: Ollama = None
    rag: RAG = None
    container: Container = None
    pycapsule: PyCapsule_HumanEval = None

    try:
        ollama = Ollama(model = "codellama", enable_chat_history=True) # default: mistral, enable_chat_history=False
        container = Container() # default: synkrasis, synkrasis_alpha
        pycapsule = PyCapsule_HumanEval(container, ollama)
        df = HumanEvalDataset()
        
        solve_count = 0
        while True:
            data_point = df.next()
            
            if data_point is None or df.current_index == 3:
                break
            
            solve_flag = pycapsule(data_point)
            
            if solve_flag == 0:
                solve_count += 1
                print("#"*50)
                print(f"Solved {solve_count} problems")
                print("#"*50)
        
    finally:
      # warning resource_tracker: There appear to be .* leaked semaphore objects"
      call_cleanup([llm, embedding_model, vector_db, ollama, rag, container, pycapsule])

if __name__ == '__main__':
    main()
