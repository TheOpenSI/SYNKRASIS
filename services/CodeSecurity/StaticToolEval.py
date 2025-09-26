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

                
    def _run_evaluation_for_each_candidate(self, sample_index: int) -> list[dict]:
        self._run_evaluation_for_each_static_tool(sample_index)
    
        
    def _load_default_static_tools(self) -> list[StaticToolBase]:
        """
        Load default static analysis tools: CodeQL and Semgrep.
        
        Returns:
            list[StaticToolBase]: List of default static analysis tool instances.
        """
        return [CodeQL(self), Semgrep(self)]
        # return [Semgrep(self)]
        
        
    def _check_if_static_tools_loaded(self) -> None:
        """
        Ensure that static tools are loaded before proceeding.
        
        Raises:
            ValueError: If static tools are not loaded.
        """
        if self.static_tools is None:
            self.logger.error("Static tools not loaded. Please load static tools before setting up directories.")
            raise ValueError("Static tools not loaded. Please load static tools before setting up directories.")
        
        
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
    
    
    def _get_consolidated_file_name(self):
        return "_".join([st.tool_name for st in self.static_tools])
    
    
    def _run_evaluation_for_each_static_tool(self, sample_index: int) -> list[dict]:
        """
        Run evaluation for each static analysis tool on a given sample.

        Args:
            sample_index (int): Index of the sample being evaluated.
            
        Returns:
            list[dict]: List of analysis results from each static tool.
        """
        results_for_all_tools = []
        for tool in self.static_tools:
            self.logger.info(f"Running analysis with {tool.tool_name} on sample {sample_index}.")
            cmd = tool.build_command(sample_index)
            self.logger.debug(f"Constructed command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Error running {tool.tool_name} on sample {sample_index}: {result.stderr}")
                print_error(f"Error running {tool.tool_name} on sample {sample_index}: {result.stderr}")
            else:
                self.logger.info(f"{tool.tool_name} analysis completed successfully on sample {sample_index}.")
                # print_success(f"{tool.tool_name} analysis completed successfully on sample {i}.")
            
            # Analysis
            output_file = self.base_path / tool.output_dir / tool.get_output_file(sample_index)
            if not output_file.exists():
                self.logger.error((f"Expected output file {output_file} not found "
                                    f"for {tool.tool_name} on sample {sample_index}."))
                print_error((f"Expected output file {output_file} not found "
                                f"for {tool.tool_name} on sample {sample_index}."))
                continue
            
            results = tool.run_analysis(str(output_file))
            
            # save
            results_for_all_tools.append({
                "tool": tool.tool_name,
                "analysis_results": results,
            })
            
            # log
            print_info((f"Analysis results from {tool.tool_name} on "
                        f"sample {sample_index}: Found {len(results)} issues."))
            self.logger.info((f"Analysis results from {tool.tool_name} on "
                                f"sample {sample_index}: Found {len(results)} issues."))
        
        return results_for_all_tools