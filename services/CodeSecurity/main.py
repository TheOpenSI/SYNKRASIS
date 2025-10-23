# =============================================================================================
# Runs the evaluators to collect prediction data
# =============================================================================================
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import time, json

from pathlib import Path

from services.CodeSecurity.evaluators.StaticToolEval import StaticToolEval
from services.CodeSecurity.evaluators.LLMEval import LLMEval
from services.LLM.Ollama.OllamaClient import OllamaClient

def llm_result_consolidator(file_paths: list[str]) -> None:
    """
    Consolidator patch to make the LLM experiments efficient.

    Args:
        file_paths (list[str]): List of file paths to the LLM result JSON files.
    """
    dataset_name = Path(file_paths[0]).stem.split("_")[0]
    data: list[dict] = []
    
    for file_path in file_paths:
        with open(file_path, "r") as f:
            result = json.load(f)
            data.append(result)
    data_length = len(data[0])
    
    if not all(len(d) == data_length for d in data):
        raise ValueError("Inconsistent dataset lengths in provided files.")
    
    consolidated_result = []
    for i in range(data_length):
        entry = {"sample_index": i,
                 "true_label": "",
                 "analysis": []}
        
        for model_data in data:
            if entry["true_label"] == "":
                entry["true_label"] = model_data[i]["true_label"]
            entry["analysis"].extend(model_data[i]["analysis"])
    
        consolidated_result.append(entry)
    
    model_names = ["_".join(Path(file_path).stem.split("_")[1:]) for file_path in file_paths]
    consolidated_output_path = "_".join([dataset_name] + model_names) + ".json"
    target_path = Path(file_paths[0]).parent / consolidated_output_path
    with open(target_path, "w") as f:
        json.dump(consolidated_result, f, indent=4)


if __name__ == "__main__":
    # Static Tool
    # -------------------------------------------
    # evaluator = StaticToolEval(
    #     dataset_path= "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/data/SecurityEval.jsonl",
    #     vul_code_key="Insecure_code",
    #     true_label_key="ID",
    #     true_label_processing_func=lambda x: x.split("_")[0]
    # )
    
    # evaluator.load_static_tools()
    # evaluator.run_evaluation()
    
    # LLM
    # -------------------------------------------
    llm_model_names = ["qwen2.5-coder:32b", 
                       "mistral:latest", 
                       "qwen2.5-coder:latest", 
                       "llama3.1:latest",
                       "phi4",
                       "deepseek-coder:6.7b"]
    
    llm_models = [OllamaClient(model_name=name, 
                               container_name="localhost",
                               suppress_stdout=True) for name in llm_model_names]
    
    # Loading weights takes a while, so for LLMs we run the whole dataset at once.
    saved_result_paths = []
    for llm_model in llm_models:
        evaluator = LLMEval(
            dataset_path = "/home/adnana/workspace/SYNKRASIS/services/CodeSecurity/data/SecurityEval.jsonl",
            vul_code_key = "Insecure_code",
            true_label_key = "ID",
            true_label_processing_func = lambda x: x.split("_")[0],
            llm_models = [llm_model]
        )
        evaluator.run_evaluation()
        saved_result_paths.append(evaluator.consolidated_output_path)
        
        time.sleep(20) # to unload the weights from VRAM
        
    # Consolidate results
    llm_result_consolidator(saved_result_paths)