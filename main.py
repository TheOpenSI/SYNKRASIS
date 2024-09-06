import os, sys, readline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from Services.LLM.LLM import LLM
from Services.Embedding.Embedding import EmbeddingModel
from Services.VectorDatabase.VectorDatabase import VectorDatabase
from Services.Ollama.Ollama import Ollama
from utils.output_message_format.output_colour import print_model_output, print_info
from utils.resource.resource_mg_util import call_cleanup

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))

def main():
    ollama_agent = Ollama()
    
    try:
      while True:
        user_input = input("[INPUT] Enter a question: ")
        
        if user_input == "exit":
            break
          
        print_model_output(ollama_agent.generate_response(user_input), ollama_agent.model)
        
    finally:
      # warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup()

if __name__ == '__main__':
    main()