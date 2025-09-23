import json, os, sys
from pathlib import Path

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