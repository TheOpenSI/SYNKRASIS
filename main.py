import os
import sys
import pandas as pd
import yaml
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Ollama.OllamaContainer import OllamaContainer
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from services.Container.Container import Container
from services.PyCapsule.PyCapsule import PyCapsule

# Utils
from utils.output_message_format.output_colour import print_error
from utils.resource.resource_mg_util import call_cleanup

def argument_parser():
    args = argparse.ArgumentParser(description="PyCapsule")
    args.add_argument("--query", type=str, help="User query", required=True)
    return args.parse_args()
    
    
def main():
    try:
        # PyCapsule Config
        with open("config_files/pycapsule.yaml", "r") as f:
            pycapsule_config = yaml.safe_load(f)
        
        # Container
        # Do not change this, use the default values only.
        # Refer to the external volume in docker-compose.yml
        container = Container()
        
        # LLM
        if pycapsule_config["model_medium"] == "ollama":
            llm = OllamaContainer(model_name=pycapsule_config["model_name"],
                         enable_chat_history=True,
                         max_history=pycapsule_config["conversation_history"],
                         verbose_switch=False,
                         container_name=pycapsule_config["ollama_container_name"])
            
        elif pycapsule_config["model_medium"] == "openai":
            llm = OpenAI_GPT(model_name=pycapsule_config["model_name"],
                             enable_chat_history=True,
                             max_history=pycapsule_config["conversation_history"])
        else:
            print_error("Invalid model medium, check PyCapsule config.")
            raise ValueError("Invalid model medium, check PyCapsule config.")
        
        # PyCapsule
        pycapsule = PyCapsule(pycapsule_container=container, 
                              llm=llm,
                              maximum_attempts=pycapsule_config["maximum_attempts"])
        
        # Arguments
        args = argument_parser()
        
        # PyCapsule
        pycapsule(user_query = args.query)
        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([llm])


if __name__ == '__main__':
    main()