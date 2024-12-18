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

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from utils.main.main_experiment_helper import parse_arguments, append_result_to_dataloader, safe_save_data, setup

# Data
from data.DatasetBase import DatasetBase
from data.MBPP.MBPP import MBPP
from data.HumanEval.HumanEval import HumanEval

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "config_files/llm_config.yaml"))   

def main():
    # Arguments
    main_args = parse_arguments()
    # qwen = Ollama(model_name = "qwen2.5-coder", enable_chat_history = True)
    gpt = OpenAI_GPT(model_name = "gpt-3.5-turbo-1106", enable_chat_history = True)
    # Setup
    dataloader, container, pycapsule = setup(main_args, gpt)
    
    try:
        print_info(f"Starting gpt {main_args.dataset} experiment")
        
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
        
        safe_save_data(dataloader, "humaneval_et", pycapsule.llm.model_name)
        
    finally:
        call_cleanup([gpt, container, pycapsule])

if __name__ == "__main__":
    main()