import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from Agents.benchmark.BenchmarkRunner import BenchmarkRunner
from utils.ascii.synkrasis import print_synkrasis_logo

# Candidate models as "backend:model", backend is openai or ollama, e.g. "ollama:llama3.1:8b"
MODELS = ["openai:gpt-5-nano-2025-08-07"]

# At most 2 judges, keep them constant across runs
JUDGES = ["openai:gpt-5-mini-2025-08-07", "openai:gpt-5.4-mini-2026-03-17"]


def main():
    print_synkrasis_logo()
    runner = BenchmarkRunner(models=MODELS,
                             judges=JUDGES,
                             prompt_version="0_3",
                             case_ids=None, # None = all 10 development cases
                             run_name="baseline_v03")
    summary = runner.run()
    print(summary.to_string())


if __name__ == '__main__':
    main()
