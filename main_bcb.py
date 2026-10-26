import os
import subprocess
import sys
import traceback
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bcb_report import results_path, save_report
from data.BigCodeBench.BigCodeBench import BigCodeBench
from lcb_report import BASELINE_RUN, failed_with_assertion, load_results
from services.Container.Container import Container
from services.LLM.Ollama.OllamaContainer import OllamaContainer
from services.PyCapsule.PyCapsule_BigCodeBench import PyCapsule_BigCodeBench
from utils.ascii.synkrasis import print_synkrasis_logo
from utils.resource.resource_mg_util import call_cleanup

MODEL_NAMES = ["qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5:72b"]
OUTPUT_DIR = "experiment_results/bpd/bcb_qwen2.5"
NUM_PROBLEMS = None                 # None = all 1140 tasks
MAX_ATTEMPTS = 5                    # fix attempts after the first generation
TEST_TIMEOUT = 30                   # seconds per unit test
TOTAL_TIMEOUT = 300                 # seconds for all the unit tests of a task together, as in the original runs

OLLAMA_CONTAINER_NAME = "ollama"
OLLAMA_PORT = 11434
OLLAMA_NUM_CTX = 16384

CONTAINER_NAME = "synk_bcb"         # made once by services/Container/prepare_bcb_container.py, it has the libraries

# (run name, BPD on, most traces in one fix query, None = a trace for every failed assertion)
# The first run is the baseline, the BPD runs only run the tasks it failed with a failed assertion.
RUNS = [(BASELINE_RUN, False, None),
        ("bpd_1_trace", True, 1),
        ("bpd_all_traces", True, None)]


class Tee:
    """Everything printed also goes to the log file."""

    def __init__(self, stream, log_file):
        self.stream = stream
        self.log_file = log_file

    def write(self, text):
        self.stream.write(text)
        self.log_file.write(text)

    def flush(self):
        self.stream.flush()
        self.log_file.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)


def container_exists() -> bool:
    listing = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True).stdout
    return CONTAINER_NAME in listing.split()


def tasks_failed_with_assertion(model_name: str, total: int) -> list[int]:
    results = load_results(results_path(model_name, OUTPUT_DIR, BASELINE_RUN))
    if results is None or len(results) != total:
        raise RuntimeError(f"The run without BPD is not finished: {0 if results is None else len(results)} "
                           f"of {total} tasks.")
    task_ids = [result["task_id"] for result in results if failed_with_assertion(result)]
    print(f"{len(task_ids)} of {total} tasks failed with a failed assertion in the run without BPD.")
    return task_ids


def load_dataset(model_name: str, run_name: str) -> BigCodeBench:
    dataloader = BigCodeBench(model_name = model_name,
                              output_dir = OUTPUT_DIR,
                              suffix = f"_{run_name}",
                              is_resuming = os.path.exists(results_path(model_name, OUTPUT_DIR, run_name)))
    if NUM_PROBLEMS:
        step = max(1, len(dataloader.data) // NUM_PROBLEMS)
        dataloader.data = dataloader.data.iloc[::step].head(NUM_PROBLEMS).reset_index(drop = True)
    return dataloader


def run(llm, model_name: str, container: Container, run_name: str, use_bpd: bool, max_traces) -> None:
    print(f"\n===== {model_name}: {run_name} =====")
    pycapsule = PyCapsule_BigCodeBench(
        pycapsule_container = container,
        llm = llm,
        maximum_attempts = MAX_ATTEMPTS,
        per_test_timeout = TEST_TIMEOUT,
        total_timeout = TOTAL_TIMEOUT,
        enable_bpd = use_bpd,
        max_traces = max_traces,
        calls_log_path = os.path.join(OUTPUT_DIR, f"{model_name}_bcb_calls_{run_name}.jsonl"))

    dataloader = load_dataset(model_name, run_name)
    try:
        if run_name != BASELINE_RUN:
            baseline_total = len(load_dataset(model_name, BASELINE_RUN).data)
            dataloader.select_tasks(tasks_failed_with_assertion(model_name, baseline_total))
        print(f"Running {len(dataloader.data)} tasks, {dataloader.current_index} already done")
        pycapsule.run_pycapsule_experiment(dataloader)
    except Exception as e:
        print(f"Run failed for {run_name}: {e}")
        traceback.print_exc()
    finally:
        call_cleanup([pycapsule])


def run_model(model_name: str, container: Container) -> None:
    llm = None
    try:
        llm = OllamaContainer(model_name = model_name,
                              enable_chat_history = True,
                              max_history = 1,
                              verbose_switch = False,
                              container_name = OLLAMA_CONTAINER_NAME,
                              local_port = OLLAMA_PORT,
                              num_ctx = OLLAMA_NUM_CTX)
        for run_name, use_bpd, max_traces in RUNS:
            run(llm, model_name, container, run_name, use_bpd, max_traces)
        print("\n" + save_report(model_name, OUTPUT_DIR))
    except Exception as e:
        print(f"Run failed for {model_name}: {e}")
        traceback.print_exc()
    finally:
        call_cleanup([llm])


def main():
    os.makedirs(OUTPUT_DIR, exist_ok = True)
    log_file = open(os.path.join(OUTPUT_DIR, "run.log"), "a")
    sys.stdout = Tee(sys.stdout, log_file)
    sys.stderr = Tee(sys.stderr, log_file)

    print_synkrasis_logo()
    if not container_exists():
        print(f"The container {CONTAINER_NAME} does not exist. Run once: python services/Container/prepare_bcb_container.py")
        return

    container = None
    try:
        container = Container(container_name = CONTAINER_NAME,
                              mount_dir_name = "synk_bcb_mount",
                              timeout = 1800)
        for model_name in MODEL_NAMES:
            run_model(model_name, container)
    finally:
        call_cleanup([container])


if __name__ == '__main__':
    main()
