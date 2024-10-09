import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.HF_LLM.HF_LLM import HF_LLM
from services.LLM.Ollama.Ollama import Ollama
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from services.Embedding.Embedding import EmbeddingModel
from services.VectorDatabase.VectorDatabase import VectorDatabase
from services.RAG.RAG import RAG
from services.Container.Container import Container
from services.PyCapsule.PyCapsule import PyCapsule
from services.PyCapsule.PyCapsule_MBPP import PyCapsule_MBPP

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup

# Data
from data.MBPP.MBPP import MBPP

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))

def main():
    # All services
    llm: HF_LLM = None
    ollama: Ollama = None
    openai: OpenAI_GPT = None
    embedding_model: EmbeddingModel = None
    vector_db: VectorDatabase = None
    rag: RAG = None
    container: Container = None
    pycapsule: PyCapsule = None

    try:
        df = MBPP()
        openai = OpenAI_GPT(enable_chat_history = True)
        container = Container()
        pycapsule = PyCapsule_MBPP(container, openai)
        
        while True:
            data_point = df.next()
            
            if data_point is None:
                break
            
            solve_flag, fix_mode_attempt_count = pycapsule(data_point)
            status = "fail"
            
            if solve_flag == 0:
                df.solved_count += 1
                status = "pass"
            else:
                df.unsolved_count += 1
                
                
            df.results.append({
                "task_id": data_point["task_id"],
                "fix_mode_attempt_count": fix_mode_attempt_count,
                "status": status
            })
            
            print("#" * 50)
            print(f"Solved {df.solved_count} problems, Unsolved {df.unsolved_count} problems")
            print("#" * 50)
            
            df.log_to_csv(openai.model)
        
        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm, embedding_model, vector_db, ollama, rag, container, pycapsule, openai])

if __name__ == '__main__':
    main()
