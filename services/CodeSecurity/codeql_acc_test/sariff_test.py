import json, os, sys
from pathlib import Path

DATA_PATH = "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/data/python_cyber_native.jsonl"
CODEQL_RESULT_DIR = "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/codeql_acc_test/output"

def get_sarif_files(dir: str) -> list[Path]:
    """
    Get all SARIF files in a directory

    Args:
        dir (str): The directory to search for SARIF files.

    Returns:
        list[Path]: A list of Path objects representing the SARIF files found.
    """
    return [file for file in Path(dir).iterdir()]

def analyse_sarif(file_path: Path) -> list:
    """
    Analyze a SARIF file and extract relevant information.

    Args:
        file_path (Path): The path to the SARIF file.
    
    Returns:
        list: A list of results extracted from the SARIF file.
    """
    with open(file_path, "r") as f:
        sarif_data = json.load(f)
            
    results = sarif_data.get("runs")[0].get("results")
    
    return results


def check_if_same():
    sarif_files = get_sarif_files(CODEQL_RESULT_DIR)
    
    # CyberNative
    with open(DATA_PATH, 'r') as f:
        cyber_native_data = [json.loads(line) for line in f]
        


if __name__ == "__main__":
    sarif_files = get_sarif_files(CODEQL_RESULT_DIR)
    for file in sarif_files:
        results = analyse_sarif(file)
        print(f"File: {file.name}, Total issues found: {len(results)}")