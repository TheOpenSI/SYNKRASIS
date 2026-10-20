import os
import sys
import traceback
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.Container.Container import Container
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench
# from services.PyCapsule.PyCapsule_BigCodeBench import PyCapsule_BigCodeBench

# Utils
from utils.resource.resource_mg_util import call_cleanup
from utils.ascii.synkrasis import print_synkrasis_logo
from utils.output_message_format.output_colour import print_error

# data
from data.LiveCodeBench.LiveCodeBench import LiveCodeBench
# from data.BigCodeBench.BigCodeBench import BigCodeBench

# report
from lcb_report import BASELINE_RUN, BPD_RUN, failed_with_assertion, load_results, results_path, save_report


# Every model runs the whole experiment, one after the other. Fill in the names:
# - Ollama: the name as in `ollama list`, e.g. "qwen2.5-coder:7b". Needs the ollama container running once:
#       docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
#   (--gpus=all is needed for a GPU)
# - OpenAI: a name that starts with "gpt-", e.g. "gpt-4o-mini-2024-07-18". Needs OPENAI_API_KEY in the .env file.
MODEL_NAMES = ["qwen2.5:32b", "phi4:14b", "gpt-oss:20b", "qwen2.5:72b"]

NUM_PROBLEMS = None                    # None = the whole dataset (175 problems), or a number: that many, spread over the dataset
OUTPUT_DIR = "experiment_results/bpd/lcb"      # results (csv, json) and the report of every model, the log goes here too
LOG_PROMPTS = True                     # the log has the full prompt and the response of every LLM call

# ollama
OLLAMA_CONTAINER_NAME = "ollama"
OLLAMA_PORT = 11434
OLLAMA_NUM_CTX = 16384                 # long prompts (problem + code + trace) must not be cut

# generated code runs in docker: no network, 2g memory, 1 cpu, 256 processes. The BPD trace runs on this machine.
DOCKER_OPTIONS = ["--network", "none", "--memory", "2g", "--cpus", "1", "--pids-limit", "256"]


def make_llm(model_name: str):
    """
    OpenAI for a name that starts with "gpt-", else Ollama.
    The imports are here so a machine only needs the packages of the LLM it uses.
    """
    if model_name.startswith("gpt-"):
        from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
        return OpenAI_GPT(model_name = model_name,
                          enable_chat_history = True,    # needed by pycapsule, the fix queries do not send it
                          max_history = 1,
                          verbose_switch = LOG_PROMPTS)

    from services.LLM.Ollama.OllamaContainer import OllamaContainer
    return OllamaContainer(model_name = model_name,
                           enable_chat_history = True,
                           max_history = 1,
                           verbose_switch = LOG_PROMPTS,
                           container_name = OLLAMA_CONTAINER_NAME,
                           local_port = OLLAMA_PORT,
                           num_ctx = OLLAMA_NUM_CTX)


def tasks_failed_with_assertion(baseline_results_path: str, total: int) -> list[str]:
    """
    The tasks the run without BPD failed with a wrong answer. Only a wrong answer gets a BPD trace, 
    so these are the tasks where the BPD run can differ from the first run.

    Args:
        baseline_results_path (str): Results (json) of the run without BPD.
        total (int): Number of problems that run has to have finished.
    """
    results = load_results(baseline_results_path)
    if results is None or len(results) != total:
        raise RuntimeError(f"The run without BPD is not finished: {0 if results is None else len(results)} of {total} "
                           f"problems in {baseline_results_path}.")
    task_ids = [result["task_id"] for result in results if failed_with_assertion(result)]
    print(f"{len(task_ids)} of {total} problems failed with an AssertionError in the run without BPD.")
    return task_ids


def run_model(model_name: str, container: Container) -> None:
    """
    The experiment of one model: the run without BPD on all problems, then the run with BPD on the problems 
    that still failed with a wrong answer, then the report. 
    Started before and stopped? Then it continues after the last finished problem.
    """
    llm = None
    try:
        llm = make_llm(model_name)

        for run_name, use_bpd in [(BASELINE_RUN, False), (BPD_RUN, True)]:
            print(f"\n===== {model_name}: {run_name} =====")
            pycapsule = PyCapsule_LiveCodeBench(pycapsule_container = container,
                                                llm = llm,
                                                maximum_attempts = 5,
                                                per_test_timeout = 10,
                                                enable_bpd = use_bpd)

            dataloader = LiveCodeBench(model_name = model_name,
                                       output_dir = OUTPUT_DIR,
                                       suffix = f"_{run_name}",
                                       is_resuming = os.path.exists(results_path(model_name, OUTPUT_DIR, run_name)))
            if NUM_PROBLEMS:
                step = max(1, len(dataloader.data) // NUM_PROBLEMS)
                dataloader.data = dataloader.data.iloc[::step].head(NUM_PROBLEMS).reset_index(drop = True)

            try:
                if use_bpd:
                    # a trace only helps with a wrong answer: only run the tasks the first run failed with one
                    dataloader.select_tasks(tasks_failed_with_assertion(
                        results_path(model_name, OUTPUT_DIR, BASELINE_RUN), len(dataloader.data)))
                print(f"Running {len(dataloader.data)} problems, {dataloader.current_index} already done")
                pycapsule.run_pycapsule_experiment(dataloader)
            except Exception as e:
                print(f"Run failed for {run_name}: {e}")
                traceback.print_exc()    # a failure stops the run on purpose (no code in a response, driver error)
                continue
            finally:
                call_cleanup([pycapsule])

        print("\n" + save_report(model_name, OUTPUT_DIR))

    except Exception as e:
        print(f"Run failed for {model_name}: {e}")
        traceback.print_exc()

    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm])


def main():
    print_synkrasis_logo()
    if not MODEL_NAMES:
        print_error("MODEL_NAMES in main.py is empty, add the names of the models to run.")
        return

    container = None
    try:
        container = Container(container_name = "synk_lcb",
                              mount_dir_name = "synk_lcb_mount",
                              timeout = 1800,
                              run_options = DOCKER_OPTIONS)
        for model_name in MODEL_NAMES:
            run_model(model_name, container)

    finally:
        call_cleanup([container])


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
