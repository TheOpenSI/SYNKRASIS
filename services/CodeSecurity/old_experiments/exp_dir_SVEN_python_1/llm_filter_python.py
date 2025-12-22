import json
from pathlib import Path

sven_data_path = "services/CodeSecurity/data/SVEN.json"
full_sven_result_path = ("services/CodeSecurity/exp_dir_SVEN/"
                    "SVEN_qwen2_5_coder_32b_mistral_latest_qwen2_5_coder_latest_"
                    "llama3_1_latest_phi4_latest_deepseek_coder_6_7b_devstral_24b.json")

with open(full_sven_result_path, "r") as f:
    full_sven_data = json.load(f)

with open(sven_data_path, "r") as f:
    sven_data = json.load(f)
    
python_sven_indices: list[int] = [entry["id"] for entry in sven_data if entry["language"].lower() == "python"]
python_sven_results: list[dict] = [full_sven_data[i] for i in python_sven_indices]

python_sven_result_file_name = Path(full_sven_result_path).name

target_path = "services/CodeSecurity/exp_dir_SVEN_python/" + python_sven_result_file_name
with open(target_path, "w") as f:
    json.dump(python_sven_results, f, indent=4)