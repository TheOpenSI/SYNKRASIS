import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
from typing import Optional, List

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
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "config_files/llm_config.yaml"))


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


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PyCapsule experiments")
    parser.add_argument("--subset-size", 
                        type = int, 
                        default = None,
                        # default = 5,
                        help="Number of samples to run from each dataset. If not specified, runs full datasets.")
    
    parser.add_argument("--datasets", 
                        nargs="+", # multiple arguments 
                        choices=["ds1000", "humaneval", "mbpp"], 
                        default=["ds1000", "humaneval", "mbpp"], 
                        # default = ["ds1000"],
                        help="Specify which datasets to run. Options: ds1000, humaneval, mbpp")
    return parser.parse_args()


def get_selected_dataloaders(args: argparse.Namespace) -> List[DatasetBase]:
    dataset_map: dict[str, DatasetBase] = {
        "ds1000": DS1000(subset_size = args.subset_size),
        "humaneval": HumanEval(subset_size = args.subset_size),
        "mbpp": MBPP(subset_size = args.subset_size)
    }
    return [dataset_map[dataset] for dataset in args.datasets]


def append_result_to_dataloader(target_dataloader: DatasetBase, data_point: dict, fix_mode_attempt_count: int, status: str) -> None:
    if target_dataloader.__class__.__name__ == "DS1000":
        target_dataloader.results.append({
            "problem_id": data_point['metadata']['problem_id'],
            "library": data_point['metadata']['library'],
            "fix_mode_attempt_count": fix_mode_attempt_count,
            "status": status
        })
    else:
        target_dataloader.results.append({
            "task_id": data_point["task_id"],
            "fix_mode_attempt_count": fix_mode_attempt_count,
            "status": status
        }) 


def main():
    args = parse_arguments()
    
    # All base services
    llm: HF_LLM = None
    ollama: Ollama = None
    openai: OpenAI_GPT = None
    embedding_model: EmbeddingModel = None
    vector_db: VectorDatabase = None
    rag: RAG = None
    container: Container = None
    pycapsule: PyCapsule = None

    # Get selected dataloaders based on arguments
    all_dataloaders = get_selected_dataloaders(args)
    
    # Create corresponding containers
    container_map: dict[DatasetBase, Container] = {
        # DS1000: Container(container_name="synk_ds1000", mount_dir_name = "synk_ds1000_mount", shell_script_name = "start.sh"),
        DS1000: Container(container_name="synk_ds1000", mount_dir_name = "synk_ds1000_mount", shell_script_name = "start_rm_req.sh"), # TODO: Chnage shell script.
        HumanEval: Container(container_name="synk_humaneval", mount_dir_name = "synk_humaneval_mount", shell_script_name = "start.sh"),
        MBPP: Container(container_name="synk_mbpp", mount_dir_name = "synk_mbpp_mount", shell_script_name = "start.sh")
    }
    
    all_containers = [container_map[type(loader)] for loader in all_dataloaders]
    
    # Create corresponding PyCapsules
    pycapsule_map: dict[DatasetBase, PyCapsule] = {
        DS1000: PyCapsule_DS1000,
        MBPP: PyCapsule_MBPP,
        HumanEval: PyCapsule_HumanEval
    }
    #LLM
    openai = OpenAI_GPT(enable_chat_history=True)
    
    # By now, all containers will have the correct sequence.
    # Same openai instance will have system promopt issue if each dataset has different system prompts.
    all_pycapsules = [pycapsule_map[type(loader)](container, openai) 
                      for loader, container in zip(all_dataloaders, all_containers)]
       
    try:
        for target_dataloader, target_pycapsule in zip(all_dataloaders, all_pycapsules):
            experiment_name = target_dataloader.__class__.__name__
            print_info(f"Starting experiment: {experiment_name}")
            
            try:
                for raw_data_point in target_dataloader.data:
                    data_point = target_dataloader.process(raw_data_point)
                    solve_flag, fix_mode_attempt_count = target_pycapsule(data_point)
                    status = "fail"
                
                    if solve_flag == 0:
                        target_dataloader.solved_count += 1
                        status = "pass"
                        
                    else:
                        target_dataloader.unsolved_count += 1
                        
                    append_result_to_dataloader(target_dataloader, data_point, fix_mode_attempt_count, status)
                    
                    print("#" * 50)
                    print(f"Solved {target_dataloader.solved_count} problems, Unsolved {target_dataloader.unsolved_count} problems")
                    print("#" * 50)
                
                safe_save_data(target_dataloader, experiment_name, target_pycapsule.llm.model_name)
                
            except (Exception, KeyboardInterrupt) as exp_error:
                print_error(f"Error in experiment {experiment_name}: {str(exp_error)}")
                safe_save_data(target_dataloader, experiment_name, target_pycapsule.llm.model_name)
    
    except (Exception, KeyboardInterrupt) as e:
        print_error(f"Critical error in main execution: {str(e)}")
        for dataloader in all_dataloaders:
            safe_save_data(dataloader, dataloader.__class__.__name__, target_pycapsule.llm.model_name)
        
    finally:
        call_cleanup([llm, embedding_model, vector_db, ollama, rag, container, pycapsule, openai])
        for p in all_pycapsules:
            p.cleanup()

if __name__ == "__main__":
    main()