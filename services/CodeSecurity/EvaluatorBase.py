# ==============================================================================================
# Code Security Evaluator Base Class
# Inherity from this class to implement specific evaluation strategies.
# Child classes to implement:
#   - _get_all_dirs_to_create() -> set
#   - _get_consolidated_file_name() -> str
#   - _run_evaluation_for_each_candidate(sample_index: int) -> list[dict
#
# Usage:
#   - get_code_dir() -> str
#   - run_evaluation() -> None
# ==============================================================================================

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from tqdm import tqdm

from utils.logger.Logger import Logger
from utils.output_message_format.output_colour import print_error, print_success

class EvaluatorBase(ABC):
    def __init__(self,
                  dataset_path: str,
                  vul_code_key: str,
                  true_label_key: str,
                  code_file_name: str,
                  code_dir_name: str, 
                  base_path: str, 
                  vul_code_processing_func: callable,
                  true_label_processing_func: callable) -> None: 
        """
        Base class for code security tool evaluators.
        
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
        """
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        self.dataset_path = dataset_path
        self._filename_from_dataset = self._process_for_file_name(str(Path(self.dataset_path).stem))
        self.vul_code_key = vul_code_key
        self.true_label_key = true_label_key
        self.code_file_name = code_file_name
        self.code_dir_name = code_dir_name
        self.base_path = Path(base_path) / f"exp_dir_{self._filename_from_dataset}"
        os.makedirs(self.base_path, exist_ok=True)
        self.data = self._load_dataset()
        self.vul_process_func = vul_code_processing_func
        self.label_process_func = true_label_processing_func
        self.static_tools = None  # To be set by subclasses
        
     
    def get_code_dir(self) -> str:
        """
        Get the full path to the code directory where code files are saved.
        Useful for configuring static analysis tools.
        
        Returns:
            str: Full path to the code directory.
        """
        return str(self.base_path / self.code_dir_name)
    
    
    def run_evaluation(self) -> None:
        """
        Run the evaluation process:
        1. Setup directories
        2. Iterate over dataset entries
        3. For each entry:
            a. Extract and process vul_code and true_label
            b. Create code file
            c. Run each static analysis tool
            d. Analyze and collect results
            e. Save consolidated results
        Results are saved in a consolidated JSON file in the base_path.  
        Note: Ensure that static tools are loaded before calling this method.
        """
        # Check if static tools are loaded
        self._check_if_static_tools_loaded()
        
        # Setup directories
        self._setup_directories()
        
        # Consolidates analysis
        consolidated_output_path = \
            self.base_path / f"{self._filename_from_dataset}_{self._get_consolidated_file_name()}.json"
        all_results = []
        
        # Iterate over dataset
        for i, entry in enumerate(tqdm(self.data, 
                                       desc=f"Processing Code Samples from {Path(self.dataset_path).name}")):
            try:
                vul_code, true_label = self._get_vul_code_and_label_sample(entry)
                
                # Create code file
                self._create_code_file(vul_code)
                
                # Run each static tool
                results_for_all_candidates = self._run_evaluation_for_each_candidate(i)
                    
                # saving consolidated results
                all_results.append({
                    "sample_index": i,
                    "true_label": true_label,
                    "analysis": results_for_all_candidates
                })
                
                # saving to json
                self._save_json(consolidated_output_path, all_results)
                self.logger.info(f"Consolidated results updated at {consolidated_output_path}.")
                    
            except KeyError as e:
                self.logger.error(f"Missing key in dataset entry: {e}")
                print_error(f"Missing key in dataset entry: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error processing sample {i}: {e}")
                print_error(f"Unexpected error processing sample {i}: {e}")

    
    def _load_dataset(self) -> list:
        """
        Load dataset from the specified path.
        Supports .json and .jsonl formats.
        
        Returns:
            list: List of dataset entries (dicts).
        """
        if self.dataset_path.endswith('.jsonl'):
            self.logger.info(f"Loading dataset from JSONL file: {self.dataset_path}")
            with open(self.dataset_path, 'r') as f:
                data = [json.loads(line) for line in f]
        elif self.dataset_path.endswith('.json'):
            self.logger.info(f"Loading dataset from JSON file: {self.dataset_path}")
            with open(self.dataset_path, 'r') as f:
                data = json.load(f)
        else:
            self.logger.error("Unsupported file format. Please provide a .json or .jsonl file.")
            print_error("Unsupported file format. Please provide a .json or .jsonl file.")
            raise ValueError("Unsupported file format. Please provide a .json or .jsonl file.")
        
        self.logger.info(f"Loaded {len(data)} samples from the dataset.")
        print_success(f"Loaded {len(data)} samples from the dataset.")
        return data if isinstance(data, list) else [data]
    
    
    def _get_vul_code_and_label_sample(self, entry: dict) -> tuple[str, str]:
        """
        Extract, Process vul_code and true_label from a dataset entry.
        Args:
            entry (dict): A single dataset entry.
        Returns:
            tuple[str, str]: Processed vul_code and true_label.
        """
        self.logger.debug((f"Extracting vul_code and true_label using keys: "
                           f"{self.vul_code_key}, {self.true_label_key}"))
        # Will raise KeyError if keys are missing
        vul_code = entry[self.vul_code_key]
        true_label = entry[self.true_label_key]
        
        # Processing
        self.logger.debug("Processing vul_code and true_label if processing functions are provided.")
        vul_code = self._process_data(vul_code, "vul_code")
        true_label = self._process_data(true_label, "true_label")
        
        self.logger.debug(f"Extracted vul_code: {vul_code[:15]}... (truncated), \
            true_label: {true_label[:15]}... (truncated)")
        return vul_code, true_label
    
    
    def _create_code_file(self,
                          code: str) -> None:
        """
        Create a code file from the provided code string.

        Args:
            code (str): Code string to write to file.
        """
        self.logger.info("Creating code file from dataset...")
        with open(self.base_path / self.code_dir_name / self.code_file_name, 'w') as f:
            f.write(code)
        self.logger.info(f"Code file created at {self.base_path / self.code_dir_name / self.code_file_name}")
        
    
    def _process_data(self,
                     data_to_process: str,
                     process_type: str) -> str:
        """
        Process the data using the provided processing function.

        Args:
            data_to_process (str): The data to be processed.
            process_type (str): The type of data being processed, either "vul_code" or "true_label".

        Returns:
            str: Original or processed data.
        """
        if process_type not in ["vul_code", "true_label"]:
            self.logger.error("process_type must be either 'vul_code' or 'true_label'")
            raise ValueError("process_type must be either 'vul_code' or 'true_label'")
        
        function_to_use = self.vul_process_func \
                          if process_type == "vul_code" \
                          else self.label_process_func
        
        if function_to_use:
            self.logger.debug(f"Processing {process_type} using provided function: {function_to_use.__name__}")
            self.logger.info("Applying processing function...")
            
            processed_data = function_to_use(data_to_process)
            if not processed_data or not processed_data.strip():
                self.logger.error("Processing function returned empty or None.")
                raise ValueError("Check the processing function, it returned empty or None.")
            if not isinstance(processed_data, str):
                self.logger.error("Processing function did not return a string.")
                raise ValueError("Check the processing function, it did not return a string.")
        
            self.logger.debug(f"Processed data: {processed_data[:15]}... (truncated)")
            return processed_data
        
        # No processing
        self.logger.debug("No processing function provided, returning original data.")
        return data_to_process
    
    
    def _process_for_file_name(self, name: str) -> str:
        """
        Process a string to be safe for use as a file name without extension.

        Args:
            name (str): The original string.
        Returns:
            str: Processed string safe for file names.
        """
        safe_name = "".join(c if c.isalnum() else '_' for c in name)
        return safe_name.strip()


    def _setup_directories(self):
        self.logger.info("Setting up directory structure...")
        all_dirs_to_create = self._get_all_dirs_to_create()
        for dir_name in all_dirs_to_create:
            dir_path = Path(self.base_path) / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Created directories: {all_dirs_to_create}")
        
        
    def _save_json(self,
                   file_path: str,
                   data: Any) -> None:
        """
        Save data to a JSON file.

        Args:
            file_path (str): Path to the JSON file.
            data (Any): Data to save (should be JSON-serializable).
        """
        with open(file_path, 'w') as c_f:
            try:
                json.dump(data, c_f, indent=4)
            except TypeError as e:
                self.logger.error(f"Data {str(data)} is not JSON-serializable: {e}")
                self.logger.warning("Saving as string representation instead")
                fallback_data = {"raw_data": str(data), "error": str(e)}
                json.dump(fallback_data, c_f, indent=4)
    
    
    @abstractmethod
    def _get_all_dirs_to_create(self) -> set:
        """
        Compile a set of all directories to create based on configuration.

        Returns:
            set: Set of directory names to create.
        """
        pass
    
    
    @abstractmethod
    def _get_consolidated_file_name(self) -> str:
        """
        Generate a consolidated results file name based on candidates.

        Returns:
            str: Consolidated results file name.
        """
        pass
    
    
    @abstractmethod
    def _run_evaluation_for_each_candidate(self, sample_index: int) -> list[dict]:
        """
        Run evaluation for each analysis candidate on a specific sample.

        Args:
            sample_index (int): Index of the sample to evaluate.
            
        Returns:
            list[dict]: List of analysis results from each static tool.
        """
        pass