import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Services.LLM.llm_service import LLM
from utils.output_message_format.output_colour import print_model_output

LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))

if __name__ == '__main__':
      llm = LLM(llm_config_file =  LLM_CONFIG_FILE)
      print_model_output(llm.generate_response("Write a python function that can multiply 2 matrices."), llm.repo_name)