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
from utils.ascii.synkrasis import print_synkrasis_logo
from utils.output_message_format.output_colour import Colour

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings


def main():
    print_synkrasis_logo()
    try:
        cli_commands = CLICommands()
        
        # Key Binding
        kb = KeyBindings()

        @kb.add('tab')
        def _(event):
            """
            Key binding.

            Args:
                event: Prompt toolkit injects this.
                Contains current buffer, app state.
            """
            buffer = event.current_buffer
            suggestion = buffer.suggestion
            if suggestion:
                buffer.insert_text(suggestion.text)
                
        session = PromptSession(auto_suggest = cli_commands.auto_suggest,
                                key_bindings = kb)
        
        ollama = OllamaClient(model_name="qwen3.5:0.8b",
                                 enable_chat_history=True,
                                 max_history=10)
        while True:
            user_input = session.prompt(">> Query: ")
            
            if user_input.startswith('\\'):
                cli_commands.execute_command(user_input)
                continue
            
            ollama.generate_response(user_input, suppress_conversation_history=False)
    
    except KeyboardInterrupt:
        print_info("\nKeyboard interrupt received. Exiting...")
        
    except Exception as e:
        print_error(f"An error occurred: {e}")

        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([ollama])

if __name__ == '__main__':
    main()