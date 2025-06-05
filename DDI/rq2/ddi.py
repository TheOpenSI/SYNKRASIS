import os
import sys
import pandas as pd
import subprocess
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
        all_models = [
            "mistral:instruct",
            "devstral:24b",
            "deepseek-coder-v2:16b",
            "codestral:22b"
        #   "llama3.1:8b", 
        #   "codegemma:7b", 
        # #   "qwen3:8b", # new ollama required
        #   "devstral:24b", 
        # #   "gemma3:12b", # new ollama required
        #   "gemma2:9b",
        #   "deepseek-r1:8b", # new ollama required
        #   "granite-code:8b",
        #   "starcoder:7b",
        #   "granite3.3:8b"
        ]
        
        reset_attempts = [[2, 4], [2, 3], [1, 2], [3, 5]]
        
        for a_model, attempts in zip(all_models, reset_attempts):
            for attempt in attempts:
                try:
                    subprocess.run("docker rm pycapsule_debug_span", shell=True)
                    llm = Ollama(model_name=a_model,
                                enable_chat_history=True,
                                max_history=1,
                                verbose_switch=True)
                    
                    # llm = Claude(model_name = "claude-3-7-sonnet-20250219",
                    #              enable_chat_history=True,
                    #              max_history=1)
                    
                    container = Container(image_name="synkrasis_pycapsule", 
                                        container_name="pycapsule_debug_span",
                                        mount_dir_name=f"fs_he_{a_model}".replace(":", "_").replace(".", "_"),
                                        shell_script_name="start.sh")
                    
                    data = HumanEval(file_path="data/HumanEval/humaneval.jsonl",
                                     output_dir="experiment_results_fs",
                                     suffix = f"_fs{attempt}") # humaneval base
                    # data = HumanEval(file_path="data/HumanEval/humaneval_et.jsonl") # humaneval et
                    
                    pycapsule = PyCapsuleHE(container=container,
                                            llm=llm,
                                            maximum_attempts=5,
                                            fresh_start=attempt,
                                            ddi_output_dir="ddi_results_fs",
                                            ddi_suffix=f"_fs{attempt}")
                    
                    pycapsule.run_pycapsule_experiment(data)
                except ValueError as e:
                    continue
                except Exception as e:
                    # Caught ollama._types.ResponseError
                    print_error(f"Error running model {a_model}: {e}")
                    continue
        
        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm, container, data, pycapsule])

if __name__ == '__main__':
    main()