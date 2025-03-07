import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Ollama.Ollama import Ollama
from services.LLM.Ollama.Ollama_container import OllamaContainer
from services.Container.Container import Container
from services.PyCapsule.PyCapsule import PyCapsule
from services.LLM.HF_LLM.HF_LLM import HF_LLM

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error 
from utils.output_message_format.output_colour import print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup

def main():
    try:
        # Pycapsule
        container = Container()
        llm = OllamaContainer(model_name="qwen2.5-coder",
                              enable_chat_history=True,
                              max_history=1,
                              verbose_switch=True,
                              container_name="ollama",
                              local_port=11435)
        pycapsule = PyCapsule(container, llm, maximum_attempts=5)
        pycapsule("Write a tail recursive fibonacci function in python.")
        
        # Huggingface transformers
        llm = HF_LLM(llm_config_file="config_files/llm_config.yaml")
        llm.generate_response("Write a fibonacci function in python.")
        
        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm, container, pycapsule])

if __name__ == '__main__':
    main()