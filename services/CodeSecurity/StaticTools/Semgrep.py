from __future__ import annotations
from typing import TYPE_CHECKING

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import json

from typing import Union
from pathlib import Path

from services.CodeSecurity.StaticTools.StaticToolBase import StaticToolBase

if TYPE_CHECKING:
    from services.CodeSecurity.evaluators.StaticToolEval import StaticToolEval

class Semgrep(StaticToolBase):
    def __init__(self,
                 evaluator: StaticToolEval,
                 script_path: str = 
                    "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/scripts/run_semgrep.bash",
                 output_dir: str = "output_sem") -> None:
        required_dir_names = [output_dir]
        super().__init__(evaluator, "Semgrep", script_path, output_dir, required_dir_names)
        

    def build_command(self, index: Union[str, int]) -> list:
        # echo "Usage: $0 <python_directory> <output_file> [--verbose]"
        cmd = [
                "bash",
                self.script_path, # bash script
                str(self.evaluator.get_code_dir()), # code directory
                str(self.evaluator.base_path / self.output_dir / self.get_output_file(index)) # output file
            ]
        return cmd
    
    
    def run_analysis(self, output_path: str) -> list:
        if output_path.endswith('.json'):
            return self._analyse_json(output_path)
        
        
    def get_output_file(self, index: Union[str, int]) -> str:
        return f"results_{index}.json"
        
    
    def _analyse_json(self, file_path: str) -> list:
        """
        Analyze a Semgrep JSON file and extract relevant information.

        Args:
            file_path (str): The path to the Semgrep JSON file.
        
        Returns:
            list: A list of results extracted from the Semgrep JSON file.
        """
        with open(file_path, "r") as f:
            semgrep_report = json.load(f)
                
        # results = sg_data.get("results", [])
        
        # return results \
        #        if len(results) == 0 \
        #        else results[0].get("extra").get("metadata").get("cwe")
        
        vulnerabilities = []
        
        for result in semgrep_report['results']:
            vuln_info = {
                'type': result['check_id'],
                'description': result.get('extra', {}).get('message', ""),
                'severity': result['extra']['metadata'].get('severity', ""),
                'cwes': result['extra']['metadata'].get('cwe', []),
                'owasp': result['extra']['metadata'].get('owasp', []),
                'file': result['path'],
                'line': result.get('start', {}).get('line', -1),
                'confidence': result['extra']['metadata'].get('confidence', ""),
                'impact': result['extra']['metadata'].get('impact', ""),
            }
            vulnerabilities.append(vuln_info)
        
        return vulnerabilities