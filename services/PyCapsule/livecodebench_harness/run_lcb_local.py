# =============================================================================================
# Local (no docker) PyCapsule run on LiveCodeBench.
# Usage (from the repo root):
#   python services/PyCapsule/livecodebench_harness/run_lcb_local.py --num-problems 20 \
#       --model gpt-5-nano-2025-08-07 --output-dir experiment_results/lcb_local
#
# Saves under --output-dir:
#   - <model>_LiveCodeBench_results.{csv,json}      pass/fail per task
#   - responses/task_<id>/attempt_<n>_{query,response}.txt   raw LLM traffic
#   (run logs are written by tee-ing stdout, see the command used by the caller)
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import argparse
import types

try:
    import scipy.optimize  # noqa: F401
except ModuleNotFoundError:
    # scipy is only used by DDI (fresh_start experiments), not needed here.
    sys.modules["scipy"] = types.ModuleType("scipy")
    sys.modules["scipy.optimize"] = types.ModuleType("scipy.optimize")
    sys.modules["scipy.optimize"].curve_fit = None

from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from services.Container.LocalContainer import LocalContainer
from services.PyCapsule.PyCapsule_LiveCodeBench import PyCapsule_LiveCodeBench
from data.LiveCodeBench.LiveCodeBench import LiveCodeBench


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-problems", type=int, default=20)
    parser.add_argument("--model", default="gpt-5-nano-2025-08-07")
    parser.add_argument("--output-dir", default="experiment_results/lcb_local")
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=10, help="seconds per test case")
    args = parser.parse_args()

    dataloader = LiveCodeBench(model_name = args.model, output_dir = args.output_dir)

    # Evenly spaced sample so we get a natural mix of AtCoder (stdin) and LeetCode (functional).
    step = max(1, len(dataloader.data) // args.num_problems)
    dataloader.data = dataloader.data.iloc[::step].head(args.num_problems).reset_index(drop=True)
    print(f"Selected {len(dataloader.data)} problems: {dataloader.data['question_id'].tolist()}")

    llm = OpenAI_GPT(model_name = args.model, enable_chat_history = True, max_history = 1)
    container = LocalContainer(mount_dir_name = "synk_lcb_local", timeout = 600)
    pycapsule = PyCapsule_LiveCodeBench(pycapsule_container = container,
                                        llm = llm,
                                        maximum_attempts = args.max_attempts,
                                        timeout = args.timeout,
                                        response_log_dir = os.path.join(args.output_dir, "responses"))
    try:
        pycapsule.run_pycapsule_experiment(dataloader)
    finally:
        pycapsule.cleanup()
        llm.cleanup()


if __name__ == "__main__":
    main()
