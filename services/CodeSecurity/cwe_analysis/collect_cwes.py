# ============================================================================================
# Collect all CWEs from the latest CWE PDF from MITRE
# Saves unique CWEs to a text file
# ============================================================================================
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../")

import re

from utils.content_extractor.ContentExtractor import ContentExtractor

def main():
    CWE_MITRE_PDF = "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/data/cwe/cwe_latest.pdf"
    CWE_PATTERN = r"CWE-\d+"
    
    extractor = ContentExtractor()
    extraction_result = extractor.extract_with_fitz(CWE_MITRE_PDF)
    
    if extraction_result["success"]:
        content = extraction_result["content"]
        cwes = re.findall(CWE_PATTERN, content)
        unique_cwes = set(cwes)
        
        print(f"Total CWEs found: {len(cwes)}")
        print(f"Unique CWEs found: {len(unique_cwes)}")
        print("Saving unique CWEs to file...")
        save_cwes_to_file(unique_cwes)
    
    else:
        print(f"Error during extraction: {extraction_result['error']}")
        

def save_cwes_to_file(cwes: set[str], 
                      output_file: str = \
                          ("/home/s448780/workspace_hcc4/SYNKRASIS/"
                           "services/CodeSecurity/data/cwe/unique_cwes.txt")) -> None:
    with open(output_file, 'w') as f:
        for cwe in sorted(cwes):
            f.write(f"{cwe}\n")
    print(f"Unique CWEs saved to {output_file}")
    
    
if __name__ == "__main__":
    main()