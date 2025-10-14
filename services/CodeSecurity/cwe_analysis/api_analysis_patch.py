# This patch is to fix the initial analysis files that had issues with relationships.
# Issue: Saved data had issues with relationship description.
# Such as it would omit relationships if it does not match dcertain description.
# It reads both raw and processed files, extracts and processes the relationships,
# and updates the processed files in each CWE folder accordingly.
# ==================================================================================================

import os
import json
from pathlib import Path

def _load_results(analysis_file_paths: list[str]) -> tuple[dict, dict]:
    raw_data = {}
    processed_data = {}
    for file_path in analysis_file_paths:
        file_path = Path(file_path)
        if "raw" in file_path.stem:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)
        else:
            with open(file_path, 'r') as f:
                processed_data = json.load(f)

    return raw_data, processed_data


def _process_relationships(raw_parents: list[dict], 
                           raw_children: list[dict]) -> tuple[list[dict], list[dict]]:
    parents_to_update = {}
    children_to_update = {}
    for nodes, collector, relationship_type in [(raw_parents, parents_to_update, "parents"), 
                             (raw_children, children_to_update, "children")]:
        for node in nodes:
            if node["Type"] != "view":
                if node["Type"] == "category":
                    collector.setdefault("category_" + relationship_type, []).append(node["ID"])
                else:
                    collector.setdefault("weakness_" + relationship_type, []).append((node["Type"], 
                                                                             node["ID"]))
    return parents_to_update, children_to_update


def fix_processed_files(analysis_file_paths: list[str]) -> None:
    raw_data, processed_data = _load_results(analysis_file_paths)
    cwe_id = raw_data["test_info"]["test_cwe_id"]
    parent_key = f"/cwe/{cwe_id}/parents"
    child_key = f"/cwe/{cwe_id}/children"
    
    raw_parents = raw_data["results"][parent_key]["data"]
    raw_children = raw_data["results"][child_key]["data"]
    
    parents_to_update, children_to_update = _process_relationships(raw_parents, raw_children)
    
    # Update processed data
    processed_data["results"][parent_key] = parents_to_update
    processed_data["results"][child_key] = children_to_update
    processed_file_path = [path for path in analysis_file_paths if "processed" in path][0]
    with open(processed_file_path, 'w') as f:
        json.dump(processed_data, f, indent=2)


def main():
    base_path = Path("/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/cwe_analysis/analysis")
    all_dirs = os.listdir(base_path)
    for dir in all_dirs:
        if "CWE" in dir:
            analysis_files = os.listdir(base_path / dir)
            analysis_file_paths = [str(base_path / dir / file) for file in analysis_files]
            fix_processed_files(analysis_file_paths)

if __name__ == "__main__":
    main()