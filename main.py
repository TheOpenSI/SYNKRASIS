import os
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
# from services.LLM.HF_LLM.HF_LLM import HF_LLM
from services.LLM.Ollama.OllamaClient import OllamaClient
from services.Container.Container import Container

# Utils
from utils.output_message_format.output_colour import (
    print_model_output, 
    print_info, 
    print_error,
    print_success,
    print_warning
)
from utils.cli.CLICommands import CLICommands
from utils.resource.resource_mg_util import call_cleanup
from utils.output_message_format.output_colour import Colour
from src.synk import SynkrasisCLI

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings


def main():
    ollama = OllamaClient(model_name="qwen3.5:0.8b",
                            container_name = "192.168.0.4",
                            enable_chat_history=True,
                            max_history=10,
                            keep_alive="2m",
                            verbose_switch=False)
    
    cli = SynkrasisCLI(model=ollama)
    cli.run_cli()
    

        
    # finally:
    #     # Warning resource_tracker: There appear to be .* leaked semaphore objects"
    #     call_cleanup([ollama])

if __name__ == '__main__':
    main()