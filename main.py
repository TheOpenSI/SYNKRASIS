import os
import sys
import pandas as pd
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
        llms = ["qwen2.5-coder:7b", "qwen2.5-coder:14b"]
        for llm in llms:
            llm = Ollama(model_name = llm, verbose_switch= True)
            query_analyser = QueryAnalyser(llm=llm)
            query_analyser.run_test()

        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm])

if __name__ == '__main__':
    main()