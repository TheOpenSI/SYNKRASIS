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
from utils.main.main_experiment_helper import parse_arguments, get_selected_dataloaders, append_result_to_dataloader, safe_save_data

# Data
from data.DatasetBase import DatasetBase
from data.MBPP.MBPP import MBPP
from data.HumanEval.HumanEval import HumanEval
from data.DS1000.DS1000 import DS1000

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "config_files/llm_config.yaml"))


def main():
    # Initialize necessary services
    # qwen = HF_LLM(llm_config_file=LLM_CONFIG_FILE, enable_chat_history = True)
    qwen = Ollama(model_name = "qwen2.5-coder", enable_chat_history = True)
    container = Container(container_name = "synk_mbpp", mount_dir_name = "synk_mbpp_mount", shell_script_name = "start.sh")
    pycapsule = PyCapsule_MBPP(container, qwen)
    
    # Initialize dataset
    dataloader = MBPP()
    
    try:
        print_info("Starting mbpp-Qwen2.5 Instruct experiment")
        
        for raw_data_point in dataloader.data:
            data_point = dataloader.process(raw_data_point)
            solve_flag, fix_mode_attempt_count = pycapsule(data_point)
            status = "fail"
            
            if solve_flag == 0:
                dataloader.solved_count += 1
                status = "pass"
            else:
                dataloader.unsolved_count += 1
                
            append_result_to_dataloader(dataloader, data_point, fix_mode_attempt_count, status)
            
            print("#" * 50)
            print(f"Solved {dataloader.solved_count} problems, Unsolved {dataloader.unsolved_count} problems")
            print("#" * 50)
        
        safe_save_data(dataloader, pycapsule.llm.model_name)
            
    except (Exception, KeyboardInterrupt) as e:
        print_error(f"Error in execution: {str(e)}")
        safe_save_data(dataloader, "mbpp_qwen", pycapsule.llm.model_name)
        
    finally:
        call_cleanup([qwen, container, pycapsule])
        pycapsule.cleanup()

if __name__ == "__main__":
    main()