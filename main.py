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
from services.Finetune.Finetune import Finetune

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from services.Finetune.sample_dataset_formatting_func import formatting_func

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "config_files/llm_config.yaml"))


def main():
    try:
        llm = HF_LLM(llm_config_file = LLM_CONFIG_FILE)
        # llm.generate_response("What is the capital of France?", suppress_conversation_history=False)
        finetune = Finetune(dataset_path = "/home/s448780/workspace/synkrasis_master/services/Finetune/mbpp_finetune_data.csv",
                            format_func = formatting_func,
                            model = llm,
                            target_modules = ["q_proj","k_proj", "v_proj", "o_proj",
                                              "gate_proj","up_proj","down_proj"],
                            quantization = "4bit",
                            use_peft = True)
        finetune.train()
        finetune.generate_response("What is the capital of France?")

    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm])

if __name__ == '__main__':
    main()