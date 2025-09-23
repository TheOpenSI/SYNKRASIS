import json, os, sys
from pathlib import Path

def analyse_sg_json(file_path: Path) -> list:
    """
    Analyze a Semgrep JSON file and extract relevant information.

    Args:
        file_path (Path): The path to the Semgrep JSON file.
    
    Returns:
        list: A list of results extracted from the Semgrep JSON file.
    """
    with open(file_path, "r") as f:
        sg_data = json.load(f)
            
    results = sg_data.get("results", [])
    
    return results[0].get("extra").get("metadata").get("cwe")

if __name__ == "__main__":
    test_path = Path("/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/static_tool_acc_test/output_sem/results0.json")
    print(analyse_sg_json(test_path))