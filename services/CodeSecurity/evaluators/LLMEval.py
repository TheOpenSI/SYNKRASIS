# ==============================================================================================
# LLM-based Code Security Evaluator
# Evaluates LLMs on code security datasets.
# Creates a dataset with true labels and llm analysis results.
# Does not perform analysis itself.
# ==============================================================================================
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import re
import time

from typing import Any, Dict
from pathlib import Path
    
from services.LLM.LLMBase import LLMBase
from services.LLM.Ollama.Ollama import Ollama
from services.CodeSecurity.evaluators.EvaluatorBase import EvaluatorBase
from utils.logger.Logger import Logger
from utils.output_message_format.output_colour import print_info, print_success, print_error

class LLMEval(EvaluatorBase):
    def __init__(self,
                 dataset_path: str,
                 vul_code_key: str,
                 true_label_key: str,
                 code_file_name: str = "main.py",
                 code_dir_name: str = "vul_code",
                 base_path: str = "/home/adnana/workspace/SYNKRASIS/services/CodeSecurity/",
                 vul_code_processing_func: callable = None,
                 true_label_processing_func: callable = None,
                 llm_models: list[LLMBase] = [Ollama(model_name="qwen2.5-coder")],
                 llm_system_prompt_path: str = ("/home/adnana/workspace/SYNKRASIS/"
                                                "services/CodeSecurity/evaluators/llm_prompt/"
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
        self.is_delay_required: bool = False if len(self.llms) == 1 else True
        # consolidated output path
        self.consolidated_output_path = \
            self.base_path / f"{self._filename_from_dataset}_{self._get_consolidated_file_name()}.json"
            
            
    def _get_all_dirs_to_create(self) -> set:
        # For LLM evaluation, only need the code directory
        return set([self.code_dir_name])
    
    
    def _get_consolidated_file_name(self) -> str:
        all_model_names = [self._process_for_file_name(llm.model_name) for llm in self.llms]
        return "_".join(all_model_names)
            
            
    def _run_evaluation_for_each_candidate(self, 
                                           sample_index: int,
                                           vul_code: str) -> list[dict]:
        return self._run_evaluation_for_each_llm(sample_index, vul_code)
    
    
    def _run_evaluation_for_each_llm(self, 
                                     sample_index: int,
                                     vul_code: str) -> list[dict]:
        """
        Run evaluation for each LLM model on a given sample.

        Args:
            sample_index (int): Index of the sample being evaluated.
        
        Returns:
            list[dict]: List of evaluation results from each LLM.
        """
        # NOTE: Processing sequentially for the whole dataset would be far better.
        # NOTE: Will fix that later if required.
        self.logger.debug(f"Running LLM evaluation for sample index: {sample_index}")
        results_for_all_llms = []
        for llm in self.llms:
            self.logger.info(f"Running analysis with {llm.model_name} on sample {sample_index}.")
            user_prompt = (f"Analyse the following code for potential security vulnerabilities. "
                           f"Provide number of vulnerabilities found and "
                           f"their CWE IDs with your confidence level.\n\n"
                           f"{vul_code}")
            self.logger.debug(f"User prompt for {llm.model_name} on sample {sample_index}:\n{user_prompt}\n")
            
            # Genrate response
            self.logger.debug(f"Generating response from {llm.model_name} for sample {sample_index}.")
            response = llm.generate_response(user_prompt)
            self.logger.debug(f"Response from {llm.model_name} for sample {sample_index}:\n{response}\n")
            
            # Parse response
            parsed_response = self._parse_llm_response(response, llm.model_name)
            results_for_all_llms.append({
                "llm_model": llm.model_name,
                "parsed_response": parsed_response,
                "raw_response": response
            })
        
            print_info((f"Analysis results from {llm.model_name} on "
                        f"sample {sample_index}: CWE count {parsed_response['count']}."))
            self.logger.info("="*50)
            
            # delay
            if self.is_delay_required:
                self.logger.debug("Delaying for 2 seconds before next LLM analysis.")
                time.sleep(2)  # Delay to unload vram
        
        return results_for_all_llms
    
    
    def _parse_llm_response(self, 
                            response: str,
                            model_name: str) -> Dict:
        """
        Parse the LLM response to extract vulnerability count and CWEs.        
        Args:
            response (str): Raw LLM response
            
        Returns:
            Dict with keys: count (int), cwe (list[str]), raw_summary (str)
        """
        self.logger.debug(f"Parsing {model_name}'s response.")
        result = {
            'count': 0,
            'cwe': [],
            'raw_summary': ''
        }

        # Extract raw summary
        result['raw_summary'] = self.extract_summary(response)
            
        # Extract CWE numbers (just the numbers, not confidence)
        # Using the summary for main CWE extraction in case LLM discusses CWEs elsewhere
        cwe_matches = self.find_cwe_from_text(result['raw_summary'])
        cwe_matches_whole_response = self.find_cwe_from_text(response)
        
        result['cwe'] = list(set([f'CWE-{num}' for num in cwe_matches])) # NOTE: just numbers?
        result['_cwe_whole_response'] = list(set([f'CWE-{num}' for num in cwe_matches_whole_response]))
        
        # Extract reported vulnerability count insted of len(cwe)
        vul_match = re.search(r'Vulnerabilities Found:\s*(\d+)', response, re.IGNORECASE)
        result['reported_count'] = int(vul_match.group(1)) \
                                   if vul_match \
                                   else -1
        
        # Processed CWE Count
        result['count'] = len(result['cwe'])
        result['_cwe_whole_response_count'] = len(result['_cwe_whole_response'])
        
        # Analysis
        result["did_report_wrong"] = not result["reported_count"] == result["count"]
        result["did_discuss_other_vuls"] = result["_cwe_whole_response_count"] > result["count"]
        result["is_summary_present"] = not result["raw_summary"] == ""

        # logging
        self.logger.debug(f"Summary extracted: {result['raw_summary']}")
        self.logger.debug(f"CWEs extracted from summary: {result['cwe']}")
        self.logger.debug(f"Number of CWEs extracted from summary: {result['count']}")
        self.logger.debug(f"CWEs extracted from whole response: {result['_cwe_whole_response']}")
        self.logger.debug(f"Number of CWEs extracted from whole response: {result['_cwe_whole_response_count']}")
        self.logger.debug(f"Reported vulnerability count (in text): {result['reported_count']}")
        self.logger.debug(f"Did report wrong count: {result['did_report_wrong']}")
        self.logger.debug(f"Did discuss other vulnerabilities: {result['did_discuss_other_vuls']}")
        self.logger.debug(f"Is summary present: {result['is_summary_present']}")
        
        if result['count'] != result['reported_count']:
            self.logger.warning((f"Discrepancy in vulnerability count: "
                                 f"Reported {result['reported_count']} vs "
                                 f"Processed {result['count']}"))
            
        return result
    
    
    def find_cwe_from_text(self, text: str) -> list[str]:
        """
        Find CWE identifiers in the given text.

        Args:
            text (str): The text to search for CWE identifiers.

        Returns:
            list[str]: A list of CWE identifiers found in the text.
        """
        if text == "" or text is None:
            self.logger.debug("No text provided for CWE extraction.")
            return []
        return re.findall(r'CWE[-\s]?(\d+)', text, re.IGNORECASE)
    
    
    @staticmethod
    def extract_summary(response: str) -> str:
        """
        Extract summary section from LLM response.
        
        Matches headings like: ### Findings Summary, Summary, ***Findings Summary***, #### SUMMARY
        
        Args:
            response (str): The LLM response text
            
        Returns:
            str: The extracted summary text, or empty string if not found
        """
        pattern = r'[#]*\s?(?:Findings\s+)?Summary'
        match = re.search(pattern, response, re.IGNORECASE)
        
        if match:
            return response[match.start():].strip()
        else:
            return ""