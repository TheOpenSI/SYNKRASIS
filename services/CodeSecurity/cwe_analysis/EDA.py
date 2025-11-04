import json
from pathlib import Path
from typing import DefaultDict

cwe_data = {}
cwe_types: DefaultDict[str, int] = DefaultDict(int)
parent_categories: set[str] = set()
cwe_types_check = []
unknown_parent_ot_weak_cat: list = []
parent_types: set[str] = set()
unknown_children_ot_weak_cat: list = []
children_types: set[str] = set()
type_of_cwe_with_category_children: set[str] = set()
analysis_dir = "services/CodeSecurity/cwe_analysis/analysis"

def load_all_cwes(analysis_dir: str) -> None:
    """
    Load all processed CWE files from analysis directory
    """
    print("Loading CWE data...")
    global cwe_data
    
    for cwe_folder in Path(analysis_dir).iterdir():
        if not cwe_folder.is_dir() or not cwe_folder.name.startswith("CWE-"):
            continue
            
        cwe_id = cwe_folder.name.split("-")[1]
        processed_file = cwe_folder / f"cwe_{cwe_id}_processed_results.json"
        
        if processed_file.exists():
            with open(processed_file, 'r') as f:
                data = json.load(f)
                cwe_data[cwe_id] = data['results']
    
    print(f"Loaded {len(cwe_data)} CWEs from {analysis_dir}")
    

def eda(data: dict) -> dict:
    relationships = {}
    for cwe_id, results in data.items():
        # info
        cwe_info = results.get(f"/cwe/{cwe_id}")
        cwe_type = cwe_info.get("Type", "Unknown")
        if "category" in cwe_type.lower() and "deprecated" not in cwe_type.lower():
            cwe_types_check.append(cwe_id)
        cwe_types[cwe_type] += 1
        
        # parents
        parents = results.get(f'/cwe/{cwe_id}/parents', {})
        children = results.get(f'/cwe/{cwe_id}/children', {})
        parents_processed = _eda_parents(cwe_id, parents)
        children_processed = _eda_children(cwe_id, cwe_type, children)
        immediate_relationships = parents_processed + children_processed
        cwe_analysis = {
            "type": cwe_type,
            "immediate_relationships": immediate_relationships
        }
        relationships[cwe_id] = cwe_analysis
    return relationships
       
        
def _eda_children(cwe_id: str, type_cwe: str, children: dict) -> list:
    global children_types, unknown_children_ot_weak_cat
    
    processed_children: list = []
    for child_type, child_list in children.items():
        if "weakness" in child_type.lower():
            for l in child_list:
                if type(l) is list:
                    children_types.add(l[0])
                    try:
                        processed_children.append(l[1])
                    except Exception as e:
                        print(f"Error processing child for CWE-{cwe_id}: {e}")
                else:
                    print(f"Child weakness list is not list[list] for CWE-{cwe_id}: {child_list}")
        elif "category" in child_type.lower():
            type_of_cwe_with_category_children.add(type_cwe)
            for child in child_list:
                processed_children.append(child)
        else: 
            unknown_children_ot_weak_cat.append((cwe_id, child_type))
    
    return processed_children
        
        
def _eda_parents(cwe_id: str, parents: dict) -> list:
    global unknown_parent_ot_weak_cat
    
    processed_parents: list = []
    for parent_type, parent_list in parents.items():
        if "category" in parent_type.lower():
            processed_parents.extend(_eda_parent_category(parent_list))
        elif "weakness" in parent_type.lower():
            processed_parents.extend(_eda_parent_weakness(cwe_id, parent_list))
        else:
            unknown_parent_ot_weak_cat.append((cwe_id, parent_type))
            
    return processed_parents
            
            
def _eda_parent_category(parent_list: list[str]) -> list[str]:
    global parent_categories
    
    for parent in parent_list:
        parent_categories.add(parent)
    return parent_list
        
        
def _eda_parent_weakness(cwe_id: str, parent_list: list[list]) -> list[str]:
    global parent_types
    
    parent_ids = []
    for l in parent_list:
        if type(l) is list:
            parent_types.add(l[0])
            parent_ids.append(l[1])
        else:
            print(f"Parent weakness list is not list[list] for CWE-{cwe_id}: {parent_list}")
    return parent_ids


def parent_category_analysis(cwes: list):
    global cwe_data
    
    present = []
    prohibited = []
    for cwe in cwes:
        if cwe in cwe_data:
            present.append(cwe)
        else:
            prohibited.append(cwe)
            
    return present, prohibited

if __name__ == "__main__":
    load_all_cwes(analysis_dir)
    eda_results = eda(cwe_data)
    
    # stats
    print("\nCWE Types Distribution:")
    for cwe_type, count in cwe_types.items():
        print(f"  {cwe_type}: {count}")
    
    print("\nParent Categories:")
    print(f"  {sorted(list(int(i) for i in parent_categories))}")
    
    print("\nParent Categories Analysis:")
    present, prohibited = parent_category_analysis(parent_categories)
    print(f"  Present Categories: {sorted(list(int(i) for i in present))}")
    print(f"  Total Present: {len(present)}")
    print(f"  CWE Categories Check from title: {sorted(list(int(i) for i in cwe_types_check))}")
    print(f"  Total CWE Types Check: {len(cwe_types_check)}")
    print(f"  Prohibited Categories: {sorted(list(int(i) for i in prohibited))}")
    print(f"  Total Prohibited: {len(prohibited)}")
    
    print("\nParent Types:")
    for p_type in parent_types:
        print(f"  {p_type}")
    
    print("\nUnknown Parent Types other than weakness or categories:")
    for unknown in unknown_parent_ot_weak_cat:
        print(f"  CWE-{unknown[0]}: {unknown[1]}")
    
    print("\nChildren Types:")
    for c_type in children_types:
        print(f"  {c_type}")
    
    print("\nUnknown Children Types other than weakness:")
    for unknown in unknown_children_ot_weak_cat:
        print(f"  CWE-{unknown[0]}: {unknown[1]}")
    
    print("\nTypes of CWEs with Category Children:")
    for t in type_of_cwe_with_category_children:
        print(f"  {t}")
        
    with open("services/CodeSecurity/cwe_analysis/eda_results.json", 'w') as f:
        json.dump(eda_results, f, indent=4)