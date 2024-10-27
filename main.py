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
from services.PyCapsule.PyCapsule_DS1000 import PyCapsule_DS1000
# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
# Data
from data.DS1000.DS1000 import DS1000

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
    pycapsule: PyCapsule_DS1000 = None

    try:
        openai = OpenAI_GPT(enable_chat_history=True)
        df = DS1000()
        container = Container()
        pycapsule = PyCapsule_DS1000(container, openai)
        
        while True:
            data_point = df.next()
            
            if data_point is None:
                break
            
            solve_flag, fix_mode_attempt_count = pycapsule(data_point)
            
            # Determine status based on solve_flag
            status = "fail"
            
            # Update solved and unsolved counts
            if solve_flag == 0:
                df.solved_count += 1
                status = "pass"
            else:
                df.unsolved_count += 1
                
            # Store the result in a list
            df.results.append({
                "problem_id": data_point['metadata']['problem_id'],
                "library": data_point['metadata']['library'],
                "fix_mode_attempt_count": fix_mode_attempt_count,
                "status": status
            })
            
            # Print solved/unsolved progress
            print("#" * 50)
            print(f"Solved {df.solved_count} problems, Unsolved {df.unsolved_count} problems")
            print("#" * 50)
    
    except Exception as e:
        print_error(f"An error occurred during execution: {str(e)}")
        
    finally:
        try:
            if df is not None and hasattr(df, 'results') and df.results:
                print_info("Saving results to CSV...")
                df.log_to_csv(openai.model_name)
        except Exception as log_error:
            print_error(f"Failed to save results to CSV: {str(log_error)}")
        

if __name__ == '__main__':
    main()
