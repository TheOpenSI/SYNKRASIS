import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Ollama.Ollama import Ollama
from services.LLM.Ollama.OllamaContainer import OllamaContainer
from services.Container.Container import Container
from services.PyCapsule.PyCapsule_BigCodeBench import PyCapsule_BigCodeBench
from services.PyCapsule.PyCapsule_MBPP import PyCapsule_MBPP
from services.PyCapsule.PyCapsule_HE import PyCapsule_HE

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error 
from utils.output_message_format.output_colour import print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from utils.ascii.synkrasis import print_synkrasis_logo

# data
from data.BigCodeBench.BigCodeBench import BigCodeBench
from data.MBPP.MBPP import MBPP
from data.HumanEval.HumanEval import HumanEval


def main():
    print_synkrasis_logo()
    
    llm_model_names = ["qwen2.5-coder:7b"]

    for llm_model_name in llm_model_names:
        try:
            print(f"Running Model Now:",{llm_model_name})
            llm_name = llm_model_name
            llm = OllamaContainer(model_name = llm_name, 
                              enable_chat_history = True,
                              max_history = 1,
                              verbose_switch = False,
                              container_name = "ollama",
                              local_port=11434)
        
            container = Container(container_name = "synk_mbpp", 
                              mount_dir_name = "synk_mbpp_mount",
                              shell_script_name = "start.sh")

            pycapsule = PyCapsule_MBPP(pycapsule_container = container,
                                 llm = llm,
                                 maximum_attempts = 5)
        
            dataloader = MBPP(model_name = llm_name,
                                  is_resuming = False)
            pycapsule.run_pycapsule_experiment(dataloader)

        except Exception as e:
            print(f"Run failed for {llm_model_name}: {e}")
            continue
        
        finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
            call_cleanup([llm, container, pycapsule])

if __name__ == '__main__':
    main()
