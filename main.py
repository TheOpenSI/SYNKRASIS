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
from services.PyCapsule.PyCapsule_BigCodeBench import PyCapsule_BigCodeBench
from services.Finetune.Finetune import Finetune
from data.BigCodeBench.BigCodeBench import BigCodeBench

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from services.Finetune.sample_dataset_formatting_func import formatting_func

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "config_files/llm_config.yaml"))


def main():
    # qwen = HF_LLM(llm_config_file=LLM_CONFIG_FILE, enable_chat_history = True)
    # :7b-instruct-fp16
    qwen = Ollama(model_name = "qwen2.5-coder", enable_chat_history = True)
    # openai = OpenAI_GPT(model_name = "gpt-3.5-turbo", enable_chat_history = True)
    container = Container(container_name = "synk_bigcode", mount_dir_name = "synk_bigcode_mount", shell_script_name = "start.sh")
    pycapsule = PyCapsule_BigCodeBench(container, qwen)
    
    # Initialize dataset
    dataloader = BigCodeBench()
    
    try:
        print_info("Starting qwen 2.5 coder instruct bigcodebench experiment")
        
        while True:
            data_point = dataloader.get_next()
            if data_point is None or dataloader.current_index == 20:
                break
            solve_flag, fix_mode_attempt_count = pycapsule(data_point)
            status = "fail"
            
            if solve_flag == 0:
                dataloader.solved_count += 1
                status = "pass"
            else:
                dataloader.unsolved_count += 1
                
            dataloader.append_result(
                task_id=data_point["task_id"],
                fix_mode_attempt_count = fix_mode_attempt_count,
                status = status
            )
            
            print("#" * 50)
            print(f"Solved {dataloader.solved_count} problems, Unsolved {dataloader.unsolved_count} problems")
            print("#" * 50)
        
        dataloader.log_to_csv(model_name = pycapsule.llm.model_name)
            
    # except (Exception, KeyboardInterrupt) as e:
    #     print_error(f"Error in execution: {str(e)}")
    #     safe_save_data(dataloader, "mbpp_gpt_1106", pycapsule.llm.model_name)
        
    finally:
        call_cleanup([qwen, container, pycapsule])
        pycapsule.cleanup()

if __name__ == '__main__':
    main()