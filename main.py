import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Services.LLM.llm_service import LLM

if __name__ == '__main__':
      llm = LLM()
      llm.generate_response("What is the capital of Bangladesh?")