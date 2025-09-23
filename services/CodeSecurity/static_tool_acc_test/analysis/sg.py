import json, os, sys

def analyse_sg_json(file_path: str) -> list:
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