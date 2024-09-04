import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Services.LLM.llm_service import LLM
from utils.output_message_format.output_colour import print_model_output

if __name__ == '__main__':
      llm = LLM()
      print_model_output(llm.generate_response("Write a python function that can multiply 2 matrices."), llm.repo_name)