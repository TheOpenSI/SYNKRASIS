import os
import sys
import pandas as pd
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Ollama.Ollama import Ollama
from services.LLM.Ollama.OllamaContainer import OllamaContainer
from services.Container.Container import Container
from services.QueryAnalyser.QueryAnalyser import QueryAnalyser

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error 
from utils.output_message_format.output_colour import print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from utils.ascii.synkrasis import print_synkrasis_logo


def main():
    print_synkrasis_logo()
    try:
        llms = [
                # "qwen2.5-coder:1.5b", 
                # "qwen2.5-coder:7b", 
                # "qwen2.5-coder:14b", 
                # # "gpt-oss:20b",
                # "phi4:14b",
                # "phi4-reasoning:14b",
                # "phi4-mini:3.8b",
                "gemma3:4b",
                "gemma3:12b",
                "llama3.2:3b",
                "nemotron-3-nano:4b"]
        with open("data/QueryAnalyser/accuracy_results.json", "r") as f:
            acc: list = json.load(f)

        for llm in llms:
            verbose_switch = False
            if llm == "qwen2.5-coder:1.5b":
                verbose_switch = True
            llm = Ollama(model_name = llm, verbose_switch= verbose_switch)
            query_analyser = QueryAnalyser(llm=llm)
            llm_acc_result = query_analyser.run_test()
            acc.append(llm_acc_result)
            
            with open("data/QueryAnalyser/accuracy_results.json", "w") as f:
                json.dump(acc, f, indent=4)

        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm])

if __name__ == '__main__':
    main()