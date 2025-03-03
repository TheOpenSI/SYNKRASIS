import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Ollama.Ollama import Ollama
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from services.Container.Container import Container
from services.PyCapsule.PyCapsuleMBPP import PyCapsuleMBPP

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info
from utils.output_message_format.output_colour import print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup

# Data
from data.MBPP.MBPP import MBPP


def main():
    try:
        llm = Ollama(model_name="qwen2.5-coder", # qwen 2.5 coder instruct 7B 
                     enable_chat_history=True,
                     max_history=1,
                     verbose_switch=True)
        
        container = Container(image_name="synkrasis_pycapsule", 
                              container_name="pycapsule_debug_span",
                              mount_dir_name="pycapsule_debug_span_mount",
                              shell_script_name="start.sh")
        
        data = MBPP()
        
        pycapsule = PyCapsuleMBPP(container=container,
                                  llm=llm,
                                  maximum_attempts=5)
        
        pycapsule.run_pycapsule_experiment(data)
        
        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm, container, data, pycapsule])

if __name__ == '__main__':
    main()