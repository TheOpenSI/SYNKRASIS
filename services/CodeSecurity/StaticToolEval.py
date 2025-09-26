from __future__ import annotations
from typing import TYPE_CHECKING

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
import subprocess

from pathlib import Path
from typing import Tuple, List, Union
from tqdm import tqdm

from utils.logger.Logger import Logger
from utils.output_message_format.output_colour import print_info, print_success, print_error
from services.CodeSecurity.StaticTools.CodeQL import CodeQL
from services.CodeSecurity.StaticTools.Semgrep import Semgrep

if TYPE_CHECKING:
    from services.CodeSecurity.StaticTools. StaticToolBase import StaticToolBase


class StaticToolEval:
    def __init__(self, 
                 dataset_path: str,
                 vul_code_key: str,
                 true_label_key: str,
                 code_file_name: str = "main.py",
                 code_dir_name: str = "vul_code",
                 base_path: str = "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/",
                 vul_code_processing_func: callable = None,
                 true_label_processing_func: callable = None) -> None:
        """
        Static Code Analysis Tool Evaluation Framework

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
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        
        
    def get_code_dir(self) -> str:
        """
        Get the full path to the code directory where code files are saved.
        Useful for configuring static analysis tools.
        
        Returns:
            str: Full path to the code directory.
        """
        return str(self.base_path / self.code_dir_name)
    
    
    def load_static_tools(self,
                          static_tools: list[StaticToolBase] = None) -> None:
        """
        Load static analysis tools configuration.
        Must be called before running evaluation.
        
        Args:
            static_tools (list[StaticToolBase], optional): List of static analysis tool instances. 
                If None, default tools (CodeQL and Semgrep) will be loaded.
        """
        if static_tools is not None:
            self.logger.info("Loading provided static analysis tools configuration.")
            self.static_tools = static_tools
        else:
            self.logger.info("No static analysis tools provided, loading default configuration.")
            self.static_tools = self._load_default_static_tools()
            
    
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
            self.base_path / f"{self._filename_from_dataset}_consolidated_evaluation_results.json"
        all_results = []
        
        # Iterate over dataset
        for i, entry in enumerate(tqdm(self.data, 
                                       desc=f"Processing Code Samples from {Path(self.dataset_path).name}")):
            try:
                vul_code, true_label = self._get_vul_code_and_label_sample(entry)
                
                # Create code file
                self._create_code_file(vul_code)
                
                # Run each static tool
                results_for_all_tools = []
                for tool in self.static_tools:
                    self.logger.info(f"Running analysis with {tool.tool_name} on sample {i}.")
                    cmd = tool.build_command(i)
                    self.logger.debug(f"Constructed command: {' '.join(cmd)}")
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        self.logger.error(f"Error running {tool.tool_name} on sample {i}: {result.stderr}")
                        print_error(f"Error running {tool.tool_name} on sample {i}: {result.stderr}")
                    else:
                        self.logger.info(f"{tool.tool_name} analysis completed successfully on sample {i}.")
                        # print_success(f"{tool.tool_name} analysis completed successfully on sample {i}.")
                    
                    # Analysis
                    output_file = self.base_path / tool.output_dir / tool.get_output_file(i)
                    if not output_file.exists():
                        self.logger.error((f"Expected output file {output_file} not found "
                                           f"for {tool.tool_name} on sample {i}."))
                        print_error((f"Expected output file {output_file} not found "
                                     f"for {tool.tool_name} on sample {i}."))
                        continue
                    
                    results = tool.run_analysis(str(output_file))
                    
                    # save
                    results_for_all_tools.append({
                        "tool": tool.tool_name,
                        "analysis_results": results,
                    })
                    
                    # log
                    print_info((f"Analysis results from {tool.tool_name} on "
                                f"sample {i}: Found {len(results)} issues."))
                    self.logger.info((f"Analysis results from {tool.tool_name} on "
                                      f"sample {i}: Found {len(results)} issues."))
                    
                # saving consolidated results
                all_results.append({
                    "sample_index": i,
                    "true_label": true_label,
                    "analysis": results_for_all_tools
                })
                
                # saving to json
                with open(consolidated_output_path, 'w') as c_f:
                    json.dump(all_results, c_f, indent=4)
                self.logger.info(f"Consolidated results updated at {consolidated_output_path}.")
                    
            except KeyError as e:
                self.logger.error(f"Missing key in dataset entry: {e}")
                print_error(f"Missing key in dataset entry: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error processing sample {i}: {e}")
                print_error(f"Unexpected error processing sample {i}: {e}")
                
    
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
    
    
    def _load_default_static_tools(self) -> list[StaticToolBase]:
        """
        Load default static analysis tools: CodeQL and Semgrep.
        
        Returns:
            list[StaticToolBase]: List of default static analysis tool instances.
        """
        return [CodeQL(self), Semgrep(self)]
        # return [Semgrep(self)]
    
    
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