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
from services.PyCapsule.PyCapsule_HumanEval import PyCapsule_HumanEval
from services.PyCapsule.PyCapsule_DS1000 import PyCapsule_DS1000

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup

# Data
from data.DatasetBase import DatasetBase
from data.MBPP.MBPP import MBPP
from data.HumanEval.HumanEval import HumanEval
from data.DS1000.DS1000 import DS1000

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))


def safe_save_data(dataloader: DatasetBase, experiment_name: str, model_name: str) -> None:
    """
    Safely save data to CSV with error handling.
    Args:
        dataloader (DatasetBase): The dataloader object.
        experiment_name (str): The name of the experiment, will pass the pycapsule class name.
        model_name (str): Name of the model, used to save the data in Dataloader.
    """
    print_info(f"Saving data for {experiment_name}...")
    try:
        dataloader.log_to_csv(model_name)
    except Exception as e:
        print_error(f"Error saving data for {experiment_name}: {str(e)}")

def main():
    # All base services
    llm: HF_LLM = None
    ollama: Ollama = None
    openai: OpenAI_GPT = None
    embedding_model: EmbeddingModel = None
    vector_db: VectorDatabase = None
    rag: RAG = None
    container: Container = None
    pycapsule: PyCapsule = None

    # Data
    mbpp = MBPP()
    ds1000 = DS1000()
    human_eval = HumanEval()
    all_dataloaders: list[DatasetBase] = [ds1000, mbpp, human_eval]
    
    # LLM
    openai = OpenAI_GPT(enable_chat_history=True)
    model_name = openai.model_name  # Get the model name for logging
    
    # Container
    container = Container()
    
    # PyCapsule
    pycapsule_mbpp = PyCapsule_MBPP(container, openai)
    pycapsule_humaneval = PyCapsule_HumanEval(container, openai)
    pycapsule_ds1000 = PyCapsule_DS1000(container, openai)
    all_pycapsules: list[PyCapsule] = [pycapsule_mbpp, pycapsule_humaneval, pycapsule_ds1000]
       
    try:
        for target_dataloader, target_pycapsule in zip(all_dataloaders, all_pycapsules):
            experiment_name = target_dataloader.__class__.__name__
            print_info(f"Starting experiment: {experiment_name}")
            
            try:
                for raw_data_point in target_dataloader.data:
                    try:
                        data_point = target_dataloader.process(raw_data_point)
                        solve_flag, fix_mode_attempt_count = target_pycapsule(data_point)
                        status = "fail"
                    
                        if solve_flag == 0:
                            target_dataloader.solved_count += 1
                            status = "pass"
                        else:
                            target_dataloader.unsolved_count += 1
                            
                        target_dataloader.results.append({
                            "task_id": data_point["task_id"],
                            "fix_mode_attempt_count": fix_mode_attempt_count,
                            "status": status
                        })
                        
                        print("#" * 50)
                        print(f"Solved {target_dataloader.solved_count} problems, Unsolved {target_dataloader.unsolved_count} problems")
                        print("#" * 50)
                        
                    except Exception as data_point_error:
                        print_error(f"Error processing data point - {raw_data_point}: {str(data_point_error)}")
                
                # Save data after completing each experiment
                safe_save_data(target_dataloader, experiment_name, model_name)
                
            except Exception as exp_error:
                print_error(f"Error in experiment {experiment_name}: {str(exp_error)}")
                # Try to save whatever data we have so far
                safe_save_data(target_dataloader, experiment_name, model_name)
    
    except Exception as e:
        print_error(f"Critical error in main execution: {str(e)}")
        # Try to save data from all experiments
        for dataloader in all_dataloaders:
            safe_save_data(dataloader, dataloader.__class__.__name__, model_name)
        
    finally:
        # Cleanup resources
        call_cleanup([llm, embedding_model, vector_db, ollama, rag, container, pycapsule, openai])

if __name__ == '__main__':
    main()