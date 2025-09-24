# from __future__ import annotations

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import json

from typing import Union
from pathlib import Path

from services.CodeSecurity.StaticTools.StaticToolBase import StaticToolBase
# from services.CodeSecurity.StaticToolEval import StaticToolEval

class CodeQL(StaticToolBase):
    def __init__(self,
                 evaluator: 'StaticToolEval',
                 script_path: str = 
                    "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/scripts/run_codeql.bash",
                 db_dir: str = "db_ql",
                 output_dir: str = "output_ql",
                 binary_path: str = "/home/s448780/workspace_hcc4/codeql/codeql") -> None:
        self.db_dir = db_dir
        required_dir_names = [db_dir, output_dir]
        self.binary_path = binary_path
        super().__init__(evaluator, "CodeQL", script_path, output_dir, required_dir_names)
        

    def build_command(self, index: Union[str, int]) -> list:
        # echo "Usage: $0 <python_directory> <codeql_binary_path> <database_dir> <output_dir>"
        cmd = [
                "bash",
                self.script_path, # bash script
                str(self.evaluator.get_code_dir()), # code directory
                self.binary_path, # CodeQL binary
                str(self.evaluator.base_path / self.db_dir), # database directory
                str(self.evaluator.base_path / self.output_dir / self.get_output_file(index)) # problem/sample index
            ]
        return cmd
    
    
    def run_analysis(self, output_path: str) -> list:
        if output_path.endswith('.sarif'):
            return self._analyse_sarif(output_path)
        
    
    def get_output_file(self, index: Union[str, int]) -> str:
        return f"results_{index}.sarif"
        
        
    
    def _analyse_sarif(self, file_path: str) -> list:
        """
        Analyze a SARIF file and extract relevant information.

        Args:
            file_path (str): The path to the SARIF file.
        
        Returns:
            list: A list of results extracted from the SARIF file.
        """
        with open(file_path, "r") as f:
            sarif_data = json.load(f)
                
        results = sarif_data.get("runs")[0].get("results")
        
        return results