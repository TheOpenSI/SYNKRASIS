# Fresh-start rerun (BigCodeBench, HumanEval, LiveCodeBench): the tasks that failed with an assertion error in the no_bpd run (the BPD set), each asked
# N_CALLS times as a plain new call: the task prompt only, no chat history, no tags, no error message, no BPD.
# Results per model: <OUT>/<dataset>/<model>_results.csv and .json, one row per task, saved after every task,
# a rerun resumes from the tasks already in the json. <OUT>/<dataset>/summary.csv has the accuracy per model.
#   python main_fresh.py            all three datasets
#   python main_fresh.py bcb        or: he, lcb
import csv
import json
import os
import subprocess
import sys
import traceback
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.BigCodeBench.BigCodeBench import BigCodeBench
from data.HumanEval.HumanEval import HumanEval
from data.LiveCodeBench.LiveCodeBench import LiveCodeBench
from lcb_report import BASELINE_RUN, failed_with_assertion, load_results, results_path
from services.Container.Container import Container
from services.LLM.Ollama.OllamaContainer import OllamaContainer
from services.PyCapsule.PyCapsule_BigCodeBench import PyCapsule_BigCodeBench
from services.PyCapsule.PyCapsule_HumanEval import PyCapsule_HumanEval
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench
from utils.resource.resource_mg_util import call_cleanup

MODEL_NAMES = ["qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5:72b"]
N_CALLS = 5
OUT = "experiment_results/fresh_start"
OLLAMA_CONTAINER_NAME = "ollama"
OLLAMA_PORT = 11434
OLLAMA_NUM_CTX = 16384
LCB_DOCKER_OPTIONS = ["--network", "none", "--memory", "2g", "--cpus", "1", "--pids-limit", "256"]

# key: (name, no_bpd results folder, dataset class, pycapsule class, pycapsule options as in main_bcb.py / main_he.py / main.py,
#       docker container, mount dir, container options)
DATASETS = {"bcb": ("BigCodeBench", "experiment_results/bpd/bcb_qwen2.5", BigCodeBench, PyCapsule_BigCodeBench,
                    {"per_test_timeout": 30, "total_timeout": 300}, "synk_bcb", "synk_bcb_mount", None),
            "he": ("HumanEval", "experiment_results/bpd/he_qwen2.5", HumanEval, PyCapsule_HumanEval,
                   {"per_test_timeout": 10, "total_timeout": 10}, "synk_bcb", "synk_bcb_mount", None),
            "lcb": ("LiveCodeBench", "experiment_results/bpd/lcb_qwen2.5", LiveCodeBench, PyCapsule_LiveCodeBench,
                    {"per_test_timeout": 10, "enable_bpd": False}, "synk_lcb", "synk_lcb_mount", LCB_DOCKER_OPTIONS)}


def failed_tasks(name: str, folder: str, model_name: str) -> list:
    results = load_results(results_path(model_name, folder, BASELINE_RUN, name))
    return [r["task_id"] for r in results if failed_with_assertion(r)]


def save(rows: list[dict], path: str) -> None:
    with open(path + ".json", "w") as f:
        json.dump(rows, f, indent = 4)
    with open(path + ".csv", "w", newline = "") as f:
        writer = csv.writer(f)
        writer.writerow(["task_id"] + [f"call_{i + 1}" for i in range(N_CALLS)] + ["passed"])
        for r in rows:
            writer.writerow([r["task_id"]] + [int(p) for p in r["passes"]] + [r["passed"]])


def write_summary(name: str) -> None:
    folder = os.path.join(OUT, name)
    lines = []
    for model_name in MODEL_NAMES:
        path = os.path.join(folder, f"{model_name}_results.json")
        if os.path.exists(path):
            rows = json.load(open(path))
            if rows:
                calls = sum(len(r["passes"]) for r in rows)
                lines.append([model_name, len(failed_tasks(name, DATASETS_BY_NAME[name], model_name)), len(rows),
                              f"{100 * sum(r['passed'] for r in rows) / calls:.2f}",
                              f"{100 * sum(r['passed'] > 0 for r in rows) / len(rows):.2f}"])
    with open(os.path.join(folder, "summary.csv"), "w", newline = "") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "tasks_in_set", "tasks_done", "accuracy_per_call_%", f"solved_in_{N_CALLS}_calls_%"])
        writer.writerows(lines)


def call(pycapsule, data_point) -> bool:
    try:
        return pycapsule(data_point)[0] == 0
    except ValueError as e:         # LiveCodeBench raises when the reply has no code: a failed call
        print(f"No code: {e}")
        return False


def run_model(key: str, model_name: str, container: Container) -> None:
    name, folder, dataset_class, capsule_class, options = DATASETS[key][:5]
    out_dir = os.path.join(OUT, name)
    os.makedirs(out_dir, exist_ok = True)
    path = os.path.join(out_dir, f"{model_name}_results")
    rows = json.load(open(path + ".json")) if os.path.exists(path + ".json") else []
    done = {r["task_id"] for r in rows}

    dataloader = dataset_class(model_name = model_name, output_dir = out_dir, is_resuming = False)
    dataloader.select_tasks(failed_tasks(name, folder, model_name))
    print(f"\n===== {name} {model_name}: {len(dataloader.data)} tasks, {len(done)} already done =====")

    llm = None
    pycapsule = None
    try:
        llm = OllamaContainer(model_name = model_name, enable_chat_history = True, max_history = 1,
                              verbose_switch = False, container_name = OLLAMA_CONTAINER_NAME,
                              local_port = OLLAMA_PORT, num_ctx = OLLAMA_NUM_CTX)
        # maximum_attempts = 0: one generation and its test run, no fix attempt
        pycapsule = capsule_class(pycapsule_container = container, llm = llm, maximum_attempts = 0, **options)
        while (data_point := dataloader.get_next()) is not None:
            task_id = data_point["task_id"] if key == "lcb" else int(data_point["task_id"])
            if task_id in done:
                continue
            passes = [call(pycapsule, data_point) for _ in range(N_CALLS)]
            rows.append({"task_id": task_id, "passes": passes, "passed": sum(passes)})
            save(rows, path)
            write_summary(name)
            print(f"{name} {model_name} task {data_point['task_id']}: {sum(passes)}/{N_CALLS}")
    except Exception as e:
        print(f"Run failed for {name} {model_name}: {e}")
        traceback.print_exc()
    finally:
        call_cleanup([pycapsule, llm])


DATASETS_BY_NAME = {v[0]: v[1] for v in DATASETS.values()}


def main():
    for key in sys.argv[1:] or list(DATASETS):
        container_name, mount, options = DATASETS[key][5:]
        listing = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output = True, text = True).stdout
        if container_name not in listing.split():
            print(f"The container {container_name} does not exist, make it as for main_bcb.py / main.py.")
            continue
        container = None
        try:
            container = Container(container_name = container_name, mount_dir_name = mount, timeout = 1800,
                                  **({"run_options": options} if options else {}))
            for model_name in MODEL_NAMES:
                run_model(key, model_name, container)
        finally:
            call_cleanup([container])


if __name__ == '__main__':
    main()
