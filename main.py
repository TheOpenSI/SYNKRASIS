import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Services.LLM.llm_service import LLM
from utils.output_message_format.output_colour import print_model_output

if __name__ == '__main__':
      llm = LLM()
      print_model_output(llm.generate_response("What is the capital of Bangladesh?"), llm.repo_name.split('/')[0].upper())