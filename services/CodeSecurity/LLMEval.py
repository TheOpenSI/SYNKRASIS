import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from typing import Any
from pathlib import Path
    
from services.LLM.LLMBase import LLMBase
from services.LLM.Ollama.Ollama import Ollama
from services.CodeSecurity.EvaluatorBase import EvaluatorBase
from utils.logger.Logger import Logger
from utils.output_message_format.output_colour import print_info, print_success, print_error

class LLMEval(EvaluatorBase):
    def __init__(self,
                 dataset_path: str,
                 vul_code_key: str,
                 true_label_key: str,
                 code_file_name: str = "main.py",
                 code_dir_name: str = "vul_code",
                 base_path: str = "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/",
                 vul_code_processing_func: callable = None,
                 true_label_processing_func: callable = None,
                 llm_models: list[LLMBase] = [Ollama(model_name="qwen2.5-coder")],
                 llm_system_prompt_path: str = ("/home/s448780/workspace_hcc4/SYNKRASIS/"
                                                "services/CodeSecurity/llm_prompt/"
                                                "code_sec_cwe_prompt.txt")) -> None:
        """
        LLM-based Code Analysis Evaluation tool.

        Args:
            dataset_path (str): Path to the dataset file (.json or .jsonl).
            vul_code_key (str): Key to extract vulnerable code from dataset entries.
            true_label_key (str): Key to extract true label from dataset entries.
            code_file_name (str, optional): Name of the code file to create for analysis. 
                Defaults to "main.py".
            code_dir_name (str, optional): Directory name to store code files.
            base_path (str, optional): Base path for experiment directories.
                Will add dastaset name to this path.
                Defaults to "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/".
            vul_code_processing_func (callable, optional): Function to process vul_code. 
                Should take a string and return a processed string, e.g. Remove backticks.
                Defaults to None.
            true_label_processing_func (callable, optional): Function to process true_label.
                Should take a string and return a processed string.
                Defaults to None.
            llm_model (LLMBase, optional): An instance of an LLM model class.
                Defaults to Ollama with "qwen2.5-coder".
            llm_system_prompt_path (str, optional): Path to the system prompt file for the LLM.
        """
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        super().__init__(dataset_path,
                         vul_code_key,
                         true_label_key,
                         code_file_name,
                         code_dir_name,
                         base_path,
                         vul_code_processing_func,
                         true_label_processing_func)
        self.llms = llm_models
        self.logger.debug(f"Using LLM model: {[llm.model_name for llm in self.llms]}")
        self.logger.debug(f"Loading LLM system prompt from: {llm_system_prompt_path}")
        for llm in self.llms:
            llm.set_system_prompt_from_file(llm_system_prompt_path)
    
    
    def run_evaluation(self):
        self._setup_directories()
        
        
        
        
    def _get_all_dirs_to_create(self) -> set:
        all_dirs = []
        for llm in self.llms:
            all_dirs.append(f"llm_{llm.model_name}")
        all_dirs.append(self.code_dir_name)
        
        self.logger.debug(f"Directories to create: {all_dirs}")
        return set(all_dirs)