# Test cwe relationships

import json
from tqdm import tqdm

MAPPING_FILE_PATH = ("/home/s448780/workspace_hcc4/SYNKRASIS/services/"
                     "CodeSecurity/cwe_analysis/cwe_relationships.json")

with open(MAPPING_FILE_PATH, "r") as f:
    cwe_mapping = json.load(f)

print(f"Checking {len(cwe_mapping)} CWEs for bidirectional relationships...")
    
for target_cwe in tqdm(cwe_mapping.keys()):
    relationships: list = cwe_mapping[target_cwe]
    for node in relationships:
        if node not in cwe_mapping.keys():
            raise ValueError(f"CWE {node} listed as related to {target_cwe}, but not found in mapping keys.")
        
        if target_cwe not in cwe_mapping[node]:
            raise ValueError(f"CWE {node} is related to {target_cwe}, but the relationship is not bidirectional.")

print("All relationships are bidirectional and valid.")