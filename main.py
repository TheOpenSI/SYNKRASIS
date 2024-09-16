import os
import sys
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from services.Base import ServiceBase
from services.LLM.LLM import LLM
from services.Embedding.Embedding import EmbeddingModel
from services.VectorDatabase.VectorDatabase import VectorDatabase
from services.RAG.RAG import RAG
from services.Ollama.Ollama import Ollama
from services.Container.Container import Container
from services.PyCapsule.PyCapsule import PyCapsule
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup

# Default config file
LLM_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config_files/llm_config.yaml'))

def main():
    # All services
    llm: LLM = None
    embedding_model: EmbeddingModel = None
    vector_db: VectorDatabase = None
    ollama: Ollama = None
    rag: RAG = None
    container: Container = None
    pycapsule: PyCapsule = None

    try:
        ollama = Ollama(model = "codellama", enable_chat_history=True) # default: mistral, enable_chat_history=False
        container = Container() # default: synkrasis, synkrasis_alpha
        pycapsule = PyCapsule(container, ollama)
        
        h_eval_prompt = '''from typing import List
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
'''
        
        pycapsule(h_eval_prompt)

    finally:
      # warning resource_tracker: There appear to be .* leaked semaphore objects"
      call_cleanup([llm, embedding_model, vector_db, ollama, rag, container, pycapsule])

if __name__ == '__main__':
    main()
