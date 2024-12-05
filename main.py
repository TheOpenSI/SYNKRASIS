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
        llm = OpenAI_GPT(enable_chat_history = True)
        container = Container()
        pycapsule = PyCapsule(pycapsule_container=container, llm=llm)
        pycapsule("Write a factorial function in Python.")

    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm, container, pycapsule])

if __name__ == '__main__':
    main()