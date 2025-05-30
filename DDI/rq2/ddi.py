import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Anthropic.Calude import Claude
from services.LLM.Ollama.Ollama import Ollama
from services.Container.Container import Container
from services.PyCapsule.PyCapsuleHE import PyCapsuleHE

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info
from utils.output_message_format.output_colour import print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup

# Data
from data.HumanEval.HumanEval import HumanEval


def main():
    try:
        llm = Ollama(model_name="codestral:22b", # qwen 2.5 coder instruct 7B 
                     enable_chat_history=True,
                     max_history=1,
                     verbose_switch=True)
        
        # llm = Claude(model_name = "claude-3-7-sonnet-20250219",
        #              enable_chat_history=True,
        #              max_history=1)
        
        container = Container(image_name="synkrasis_pycapsule", 
                              container_name="pycapsule_debug_span",
                              mount_dir_name="he_codestral",
                              shell_script_name="start.sh")
        
        data = HumanEval(file_path="data/HumanEval/humaneval.jsonl") # humaneval base
        # data = HumanEval(file_path="data/HumanEval/humaneval_et.jsonl") # humaneval et
        
        pycapsule = PyCapsuleHE(container=container,
                                llm=llm,
                                maximum_attempts=5)
        
        pycapsule.run_pycapsule_experiment(data)
        
        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm, container, data, pycapsule])

if __name__ == '__main__':
    main()