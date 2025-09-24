import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.CodeSecurity.StaticToolEval import StaticToolEval

if __name__ == "__main__":
    evaluator = StaticToolEval(
        dataset_path= "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/data/SecurityEval.jsonl",
        vul_code_key="Insecure_code",
        true_label_key="ID",
        true_label_processing_func=lambda x: x.split("_")[0]
    )
    
    evaluator.load_static_tools()
    evaluator.run_evaluation()