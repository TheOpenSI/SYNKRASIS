import json
import pandas as pd


sven_path = "services/CodeSecurity/data/SVEN/train.parquet"

def prepare_sven_data(sven_path: str = sven_path) -> dict:
    df = pd.read_parquet(sven_path)
    language_mapping = {
       "py": "python",
       "cc": "cpp",
       "cpp": "cpp",
       "c": "c",
       "h": "c"
    }
    
    stats = {
        "total_samples": len(df),
        "python_samples": len(df[df.file_name.str.endswith(".py")]),
        "cpp_samples": len(df[df.file_name.str.endswith(".cpp") | df.file_name.str.endswith(".cc")]),
        "c_samples": len(df[df.file_name.str.endswith(".c") | df.file_name.str.endswith(".h")])
    }
    
    data = []
    for i, row in enumerate(df.itertuples()):
        file_name = row.file_name
        file_extension = file_name.split(".")[-1]
        
        entry = {
            "id": i,
            "func_name": row.func_name,
            "func_src_before": row.func_src_before,
            "func_src_after": row.func_src_after,
            "vul_type": row.vul_type,
            "file_extension": file_extension,
            "language": language_mapping.get(file_extension, "unknown")
        }
        data.append(entry)
    
    target_path = "services/CodeSecurity/data/SVEN.json"
    with open(target_path, "w") as f:
        json.dump(data, f, indent=4)
    
    return stats

def prepare_sven_python(full_data_path: str) -> None:
    with open(full_data_path, "r") as f:
        full_data = json.load(f)
    python_data = [entry for entry in full_data if entry["language"] == "python"]
    target_path = "services/CodeSecurity/data/SVEN_python.json"
    with open(target_path, "w") as f:
        json.dump(python_data, f, indent=4)
    
    
if __name__ == "__main__":
    # stats = prepare_sven_data()
    # print(stats)
    prepare_sven_python("services/CodeSecurity/data/SVEN.json")