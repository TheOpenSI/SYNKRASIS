# =============================================================================================
# Runs the evaluators to collect prediction data
# =============================================================================================
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.CodeSecurity.evaluators.StaticToolEval import StaticToolEval
from services.CodeSecurity.evaluators.LLMEval import LLMEval
from services.LLM.Ollama.OllamaClient import OllamaClient

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
                       "phi4"]
    llm_models = [OllamaClient(model_name=name, 
                               container_name="localhost",
                               suppress_stdout=True) for name in llm_model_names]
    
    evaluator = LLMEval(
        dataset_path = "/home/adnana/workspace/SYNKRASIS/services/CodeSecurity/data/SecurityEval.jsonl",
        vul_code_key = "Insecure_code",
        true_label_key = "ID",
        true_label_processing_func = lambda x: x.split("_")[0],
        llm_models = llm_models
    )
    evaluator.run_evaluation(is_test=True, n_samples=5)