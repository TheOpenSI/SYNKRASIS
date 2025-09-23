import sys, os
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
import numpy as np

from sklearn.model_selection import train_test_split
from tqdm import tqdm

from services.LLM.Ollama.Ollama import Ollama

# Loading data
# cyber_native_path = ("/home/s448780/workspace_hcc4/SYNKRASIS/"
#                      "services/CodeSecurity/data/"
#                      "CyberNative_Code_Vulnerability_Security_DPO.jsonl")

# with open(cyber_native_path, 'r') as f:
#     data = [json.loads(line) for line in f if json.loads(line.strip()).get('lang') == 'python']

# # Saving filtered data
# with open(os.path.dirname(os.path.abspath(__file__)) + '/data/python_cyber_native.jsonl', 'w') as f:
#     for entry in data:
#         f.write(json.dumps(entry) + '\n')
# ------------------------------------------------------------------------------------------------------

# Loading python cyber native data
with open(os.path.dirname(os.path.abspath(__file__)) + '/data/python_cyber_native.jsonl', 'r') as f:
    data = [json.loads(line) for line in f]

training_data, test_data = train_test_split(data, train_size=0.25, random_state=42)
# -------------------------------------------------------------------------------------------------------

# Setting up teacher model
teacher_model = Ollama(model_name="qwen2.5-coder:32b")
teacher_model.set_system_prompt_from_file()

property_flag = True
finetune_data = []
for entry in tqdm(training_data):
    prompt = (f"{entry.get('question')}.\n"
              f"<Property>{1 if property_flag else 0}</Property>")
    property_flag = not property_flag

    response = teacher_model.generate_response(prompt)
    if response:
        finetune_data.append({
            "question": entry.get("question"),
            "answer": response,
            "property": 1 if property_flag else 0
        })
        
# Saving the finetuning data   
finetune_data_path = (os.path.dirname(os.path.abspath(__file__)) + 
                     "/data/finetune_cyber_native_qwen2.5_coder_32b.jsonl")
with open(finetune_data_path, 'w') as f:
    for item in finetune_data:
        f.write(json.dumps(item) + '\n')

