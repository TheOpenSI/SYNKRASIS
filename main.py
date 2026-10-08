import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# llm
# from services.LLM.Ollama.Ollama import Ollama
# from services.LLM.Ollama.OllamaContainer import OllamaContainer
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT

# Services
from services.Container.Container import Container
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench
# from services.PyCapsule.PyCapsule_BigCodeBench import PyCapsule_BigCodeBench
# from services.PyCapsule.PyCapsule_MBPP import PyCapsule_MBPP
# from services.PyCapsule.PyCapsule_HE import PyCapsule_HE

# Utils
# from utils.output_message_format.output_colour import print_model_output, print_info, print_error 
# from utils.output_message_format.output_colour import print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from utils.ascii.synkrasis import print_synkrasis_logo

# data
# from data.BigCodeBench.BigCodeBench import BigCodeBench
# from data.MBPP.MBPP import MBPP
# from data.HumanEval.HumanEval import HumanEval
from data.LiveCodeBench.LiveCodeBench import LiveCodeBench

# ---- LiveCodeBench run ---------------------------------------------------------------------------------------
LLM_NAME = "gpt-5-nano-2025-08-07"
NUM_PROBLEMS = 10                                      # evenly spread over the dataset: stdin (AtCoder) and functional (LeetCode)
USE_BPD = True                                         # BPD trace in the feedback for public tests with a wrong answer
OUTPUT_DIR = "experiment_results/bpd/lcb_nano_10_trace"
# generated code (and the BPD trace) run in docker: no network, 2g memory, 1 cpu, 256 processes
DOCKER_OPTIONS = ["--network", "none", "--memory", "2g", "--cpus", "1", "--pids-limit", "256"]


def run_livecodebench():
    llm = OpenAI_GPT(model_name = LLM_NAME, enable_chat_history = True, max_history = 1)
    # For an Ollama model: change LLM_NAME (e.g. "qwen2.5-coder:7b"), uncomment the OllamaContainer import above and use
    # llm = OllamaContainer(model_name = LLM_NAME, enable_chat_history = True, max_history = 1,
    #                       container_name = "ollama", local_port = 11434, num_ctx = 16384)
    container = Container(container_name = "synk_lcb",
                          mount_dir_name = "synk_lcb_mount",
                          timeout = 1800,
                          run_options = DOCKER_OPTIONS)
    pycapsule = PyCapsule_LiveCodeBench(pycapsule_container = container,
                                        llm = llm,
                                        maximum_attempts = 5,
                                        trace_feedback = USE_BPD,
                                        # the mount dir only keeps the LAST attempt of each task: this keeps every
                                        # query (feedback + trace) and every raw response
                                        response_log_dir = os.path.join(OUTPUT_DIR, "responses"))
    dataloader = LiveCodeBench(model_name = LLM_NAME, output_dir = OUTPUT_DIR)
    step = max(1, len(dataloader.data) // NUM_PROBLEMS)
    dataloader.data = dataloader.data.iloc[::step].head(NUM_PROBLEMS).reset_index(drop = True)
    print(f"Running {len(dataloader.data)} problems: {dataloader.data['question_id'].tolist()}")
    try:
        pycapsule.run_pycapsule_experiment(dataloader)
    except Exception as e:
        print(f"Run failed: {e}")
    finally:
        call_cleanup([llm, container, pycapsule])


def main():
    print_synkrasis_logo()
    run_livecodebench()
    
    # llm_model_names = ["qwen2.5-coder:7b"]

    # for llm_model_name in llm_model_names:
    #     try:
    #         print(f"Running Model Now:",{llm_model_name})
    #         llm_name = llm_model_name
    #         llm = OllamaContainer(model_name = llm_name, 
    #                           enable_chat_history = True,
    #                           max_history = 1,
    #                           verbose_switch = False,
    #                           container_name = "ollama",
    #                           local_port=11434)
        
    #         container = Container(container_name = "synk_mbpp", 
    #                           mount_dir_name = "synk_mbpp_mount",
    #                           shell_script_name = "start.sh")

    #         pycapsule = PyCapsule_MBPP(pycapsule_container = container,
    #                              llm = llm,
    #                              maximum_attempts = 5)
        
    #         dataloader = MBPP(model_name = llm_name,
    #                               is_resuming = False)
    #         pycapsule.run_pycapsule_experiment(dataloader)

    #     except Exception as e:
    #         print(f"Run failed for {llm_model_name}: {e}")
    #         continue
        
    #     finally:
    #     # Warning resource_tracker: There appear to be .* leaked semaphore objects"
    #         call_cleanup([llm, container, pycapsule])

if __name__ == '__main__':
    main()
