import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Ollama.Ollama import Ollama
from services.LLM.Ollama.OllamaContainer import OllamaContainer
from services.Container.Container import Container

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error 
from utils.output_message_format.output_colour import print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup
from utils.ascii.synkrasis import print_synkrasis_logo


def main():
    print_synkrasis_logo()
    try:
        llm = Ollama()
        while True:
            query = input("Enter your query (or 'exit' to quit): ")
            if query.lower() == 'exit':
                break
            llm.generate_response(query)

        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm])

if __name__ == '__main__':
    main()