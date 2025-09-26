from __future__ import annotations
from typing import TYPE_CHECKING

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
import subprocess

from pathlib import Path
from typing import Tuple, List, Union
from tqdm import tqdm

from utils.output_message_format.output_colour import print_info, print_success, print_error
from services.CodeSecurity.StaticTools.CodeQL import CodeQL
from services.CodeSecurity.StaticTools.Semgrep import Semgrep
from services.CodeSecurity.EvaluatorBase import EvaluatorBase

if TYPE_CHECKING:
    from services.CodeSecurity.StaticTools. StaticToolBase import StaticToolBase


class StaticToolEval(EvaluatorBase):
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
        super().__init__(dataset_path,
                         vul_code_key,
                         true_label_key,
                         code_file_name,
                         code_dir_name,
                         base_path,
                         vul_code_processing_func,
                         true_label_processing_func)
        self.static_tools: List[StaticToolBase] = None  # To be set by load_static_tools method
         
        
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
    
        
    def _load_default_static_tools(self) -> list[StaticToolBase]:
        """
        Load default static analysis tools: CodeQL and Semgrep.
        
        Returns:
            list[StaticToolBase]: List of default static analysis tool instances.
        """
        return [CodeQL(self), Semgrep(self)]
        # return [Semgrep(self)] 