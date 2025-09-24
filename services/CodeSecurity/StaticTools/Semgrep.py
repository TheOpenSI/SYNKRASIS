import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import json

from typing import Union
from pathlib import Path

from services.CodeSecurity.StaticTools.StaticToolBase import StaticToolBase
from services.CodeSecurity.StaticToolEval import StaticToolEval

class Semgrep(StaticToolBase):
    def __init__(self,
                 evaluator: StaticToolEval,
                 script_path: str = 
                    "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/scripts/run_semgrep.bash",
                 output_dir: str = "output_ql") -> None:
        required_dir_names = [output_dir]
        super().__init__(evaluator, "Semgrep", script_path, output_dir, required_dir_names)
        

    def build_command(self, index: Union[str, int]) -> list:
        cmd = [
                "bash",
                self.script_path, # bash script
                str(self.evaluator.get_code_dir()), # code directory
                str(index)
            ]
        return cmd
    
    
    def run_analysis(self, output_path: str) -> list:
        if output_path.endswith('.json'):
            return self._analyse_json(output_path)
        
        
    def get_output_file(self, index: Union[str, int]) -> str:
        return f"results_{index}.json"
        
    
    def analyse_json(file_path: str) -> list:
        """
        Analyze a Semgrep JSON file and extract relevant information.

        Args:
            file_path (str): The path to the Semgrep JSON file.
        
        Returns:
            list: A list of results extracted from the Semgrep JSON file.
        """
        with open(file_path, "r") as f:
            sg_data = json.load(f)
                
        results = sg_data.get("results", [])
        
        return results[0].get("extra").get("metadata").get("cwe")