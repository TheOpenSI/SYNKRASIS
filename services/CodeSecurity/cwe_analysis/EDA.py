import json
from pathlib import Path
from typing import DefaultDict

cwe_data = {}
cwe_types: DefaultDict[str, int] = DefaultDict(int) # dict with cwe type and count

# parent
unknown_parent_ot_weak_cat: list = [] # unknown parent types other than weakness or category
parent_categories: set[str] = set() # category-type parents
parent_types: set[str] = set() # weakness types of parents, exclude categories
parent_category_types: set[str] = set() # category types encountered

# cwe_types_unchecked: set[str] = set()
cwe_types_check: list[str] = []

# children
unknown_children_ot_weak_cat: list = [] # unknown children types other than weakness or category
children_categories: set[str] = set() # category-type children
children_types: set[str] = set() # weakness types of children, exclude categories
type_of_cwe_with_category_children: set[str] = set() # types of CWEs which have category-type children
cwes_with_category_children: list[str] = [] # list of CWE IDs which have category-type children

analysis_dir = "services/CodeSecurity/cwe_analysis/analysis" # has all the scraped CWE data


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
    global cwe_types_check, cwe_types
    
    relationships = {}
    for cwe_id, results in data.items():
        # info
        cwe_info = results.get(f"/cwe/{cwe_id}")
        cwe_type = cwe_info.get("Type", "Unknown")
        
        if "deprecated" in cwe_type.lower():
            continue
        # if "category" in cwe_type.lower() and "deprecated" not in cwe_type.lower():
        #     cwe_types_check.append(cwe_id)
        cwe_types[cwe_type] += 1
        
        # relationships
        parents = results.get(f'/cwe/{cwe_id}/parents', {})
        children = results.get(f'/cwe/{cwe_id}/children', {})
        parents_processed = _eda_parents(cwe_id, cwe_type, parents)
        children_processed = _eda_children(cwe_id, cwe_type, children)
        immediate_relationships = parents_processed + children_processed
        # if "variant" in cwe_type.lower() or "base" in cwe_type.lower():
        #     if len(children_processed) > 0:
        #         print(f"CWE-{cwe_id}, cwe-type {cwe_type} has {len(children_processed)}\
        #             children: {children_processed}")
        cwe_analysis = {
            "type": cwe_type,
            "parents": parents_processed,
            "children": children_processed,
            "immediate_relationships": immediate_relationships
        }
        relationships[cwe_id] = cwe_analysis
    return relationships
       
        
def _eda_children(cwe_id: str, cwe_type: str, children: dict) -> list:
    global children_types, unknown_children_ot_weak_cat, \
        type_of_cwe_with_category_children, cwes_with_category_children, children_categories
        
    if "category" in cwe_type.lower():
        children_categories.add(cwe_id)
    
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
            type_of_cwe_with_category_children.add(cwe_type) # category or view
            cwes_with_category_children.append(cwe_id)
            processed_children.extend(child_list)
            for child in child_list:
                children_categories.add(child)
            
        else: 
            unknown_children_ot_weak_cat.append((cwe_id, child_type))
    
    return list(set(processed_children))
        
        
def _eda_parents(cwe_id: str, cwe_type: str, parents: dict) -> list:
    global unknown_parent_ot_weak_cat, parent_category_types
    
    if "category" in cwe_type.lower():
        parent_categories.add(cwe_id)
        
    processed_parents: list = []
    for parent_type, parent_list in parents.items():
        if "category" in parent_type.lower():
            parent_category_types.add(parent_type)
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
    return list(set(parent_list))
        
        
def _eda_parent_weakness(cwe_id: str, parent_list: list[list]) -> list[str]:
    global parent_types
    
    parent_ids = []
    for l in parent_list:
        if type(l) is list:
            parent_types.add(l[0])
            parent_ids.append(l[1])
        else:
            print(f"Parent weakness list is not list[list] for CWE-{cwe_id}: {parent_list}")
    return list(set(parent_ids))


def parent_category_analysis(cwes: list):
    """
    Checks if cwe category exist in the extracted data.
    """
    global cwe_data
    
    present = []
    missing = []
    for cwe in cwes:
        if cwe in cwe_data:
            present.append(cwe)
        else:
            missing.append(cwe)
            
    return present, missing

if __name__ == "__main__":
    load_all_cwes(analysis_dir)
    eda_results = eda(cwe_data)
    
    # stats
    print("\nCWE Types Distribution:")
    for cwe_type, count in cwe_types.items():
        print(f"  {cwe_type}: {count}")
    
    print("-"*50)
    print("\nParent Categories:")
    print(f"  {sorted(list(int(i) for i in parent_categories))}")
    print("\nParent Types:")
    print(f"  {parent_types}")
    print("\nUnknown Parent Types other than weakness or categories:")
    for unknown in unknown_parent_ot_weak_cat:
        print(f"  CWE-{unknown[0]} had parent type: {unknown[1]}")
    print("\nParent Category Types Encountered:")
    print(f"  {parent_category_types}")
    
    print("-"*50)
    print("\nChildren Categories:")
    print(f"  {sorted(list(int(i) for i in children_categories))}")
    print("\nChildren Types:")
    print(f"  {children_types}")
    print("\nCWEs with Category Children:")
    print(f"  {sorted(list(int(i) for i in cwes_with_category_children))}")
    print("\nUnknown Children Types other than weakness:")
    for unknown in unknown_children_ot_weak_cat:
        print(f"  CWE-{unknown[0]} had child type: {unknown[1]}")
    print("\nTypes of CWEs with Category Children:")
    print(f"  {type_of_cwe_with_category_children}")
    
    print("-"*50)
    print("\nParent Categories Analysis:")
    all_categories = set(list(parent_categories) + list(children_categories))
    present, missing = parent_category_analysis(all_categories)
    print(f"  Present Categories: {sorted(list(int(i) for i in present))}")
    print(f"  Total Present: {len(present)}")
    # print(f"  CWE Categories Check from title: {sorted(list(int(i) for i in cwe_types_check))}")
    # print(f"  Total CWE Types Check: {len(cwe_types_check)}")
    print(f"  Missing Categories: {sorted(list(int(i) for i in missing))}")
    print(f"  Total missing: {len(missing)}")
        
    with open("services/CodeSecurity/cwe_analysis/eda_results.json", 'w') as f:
        json.dump(eda_results, f, indent=4)