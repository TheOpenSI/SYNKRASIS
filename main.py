import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from Agents.benchmark.BenchmarkRunner import BenchmarkRunner
from utils.ascii.synkrasis import print_synkrasis_logo

# Candidate models as "backend:model", backend is openai or ollama, e.g. "ollama:llama3.1:8b"
MODELS = ["ollama:gpt-oss:20b",
          "ollama:qwen3:32b",
          "ollama:qwen2.5:32b",
          "ollama:phi4:14b",
          "ollama:medgemma:27b"]

# At most 2 judges, keep them constant across runs
JUDGES = ["ollama:qwen2.5:72b", "ollama:llama3.3:70b"]


def main():
    print_synkrasis_logo()
    runner = BenchmarkRunner(models=MODELS,
                             judges=JUDGES,
                             prompt_version="0_3",
                             case_ids=None, # None = all 10 development cases
                             run_name="baseline_v03_os")
    summary = runner.run()
    print(summary.to_string())


if __name__ == '__main__':
    main()
