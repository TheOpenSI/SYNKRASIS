# ==============================================================================================
# Code Security Evaluator Base Class
# Inherity from this class to implement specific evaluation strategies.
# Child classes to implement:
#   - load_static_tools(static_tools: list[StaticToolBase]) -> None
#   - run_evaluation() -> None
# Usage:
#   - get_code_dir() -> str

# ==============================================================================================

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

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
            dataset_path (str): Path to the dataset file.
            vul_code_key (str): Key in the dataset for vulnerable code snippets.
            true_label_key (str): Key in the dataset for true vulnerability labels.
            code_file_name (str): Name of the temporary code file to create for analysis.
            code_dir_name (str): Name of the directory to store temporary code files.
            base_path (str): Base directory path for storing evaluation results.
            vul_code_processing_func (callable): Function to process vulnerable code snippets.
            true_label_processing_func (callable): Function to process true vulnerability labels.
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
    
    
    def _check_if_static_tools_loaded(self) -> None:
        """
        Ensure that static tools are loaded before proceeding.
        
        Raises:
            ValueError: If static tools are not loaded.
        """
        if self.static_tools is None:
            self.logger.error("Static tools not loaded. Please load static tools before setting up directories.")
            raise ValueError("Static tools not loaded. Please load static tools before setting up directories.")

    
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
    
    
    def _get_all_dirs_to_create(self) -> set:
        """
        Compile a set of all directories to create based on static tools configuration.

        Returns:
            set: Set of directory names to create.
        """
        self._check_if_static_tools_loaded()
        self.logger.info("Compiling list of all directories to create based on static tools configuration.")
        all_dirs = set()
        for tool in self.static_tools:
            dirs = tool.required_dir_names
            all_dirs.update(dirs)
        all_dirs.add(self.code_dir_name)
        
        self.logger.debug(f"Directories to create: {all_dirs}")
        return all_dirs
    
    
    def _setup_directories(self) -> None:
        """
        Create necessary directory structure
        """
        self.logger.info("Setting up directory structure...")
        all_dirs_to_create = self._get_all_dirs_to_create()
        for dir_name in all_dirs_to_create:
            dir_path = self.base_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Created directories: {all_dirs_to_create}")
    
    
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
    
    
    @abstractmethod
    def load_static_tools(self,
                          static_tools: list[Any]) -> None:
        """
        Load static analysis tools configuration.
        Must be called before running evaluation.
        
        Args:
            static_tools (list[Any], optional): List of static analysis tool instances. 
                If None, default tools (CodeQL and Semgrep) will be loaded.
        """
        pass
    
    
    @abstractmethod
    def run_evaluation(self) -> None:
        """
        Run the full evaluation process
        """
        pass 