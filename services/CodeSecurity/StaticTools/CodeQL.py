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

class CodeQL(StaticToolBase):
    def __init__(self,
                 evaluator: StaticToolEval,
                 script_path: str = "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/scripts/run_codeql.bash",
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
            sarif_report = json.load(f)
                
        # results = sarif_data.get("runs")[0].get("results")
        
        # return results
        results = []
    
        for run in sarif_report['runs']:
            rules = run['tool']['driver']['rules']
            
            for result in run['results']:
                rule_index = result['ruleIndex']
                rule_info = rules[rule_index]
                
                # Extract CWE information
                cwe_tags = [tag for tag in rule_info['properties']['tags'] if tag.startswith('external/cwe/')]
                cwes = [tag.split('/')[-1].upper() for tag in cwe_tags]
                
                vuln_info = {
                    'type': result['ruleId'],
                    'description': result['message']['text'],
                    'cwes': cwes,
                    'file': result['locations'][0]['physicalLocation']['artifactLocation']['uri'],
                    'line': result['locations'][0]['physicalLocation']['region']['startLine']
                }
                results.append(vuln_info)
        
        return results