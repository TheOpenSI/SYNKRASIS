# Adaptive Learning via Penalty in Hierarchical Assessment

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

from pathlib import Path

from code_security.graphs.FullCWEGraph import FullCWEGraph
from code_security.graphs.WeaknessCWEGraph import WeaknessCWEGraph

class ALPHA:
    def __init__(self, 
                 predictions_path: str,
                 eda_path: str) -> None:
        self.predictions_path = predictions_path
        self.eda_path = eda_path


    def create_full_graph(self) -> FullCWEGraph:
        """Createservices/CodeSecurity/cwe_analysis/eda_results.json full CWE graph including all types."""
        return FullCWEGraph(self.eda_path)
    
    
    def create_weakness_graph(self) -> WeaknessCWEGraph:
        """Create weakness-only CWE graph (recommended for LLM evaluation)."""
        return WeaknessCWEGraph(self.eda_path)
    
    
    def export_alpha(self,
                     output_path: str) -> None:
        weakness_cwe_graph = self.create_weakness_graph()
        # weakness_cwe_graph.calculate_and_save_depths('code_security/depth_analysis/cwe_depths.json')
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        detailed_result_path = Path(output_path).parent / f"{Path(output_path).stem}_detailed_results.json"
        
        weakness_cwe_graph.get_alpha(
            # predictions_path="services/CodeSecurity/experiments/exp_dir_SVEN_python_1/SVEN_python_qwen2_5_coder_32b_python_mistral_latest_python_qwen2_5_coder_latest_python_llama3_1_latest_python_phi4_latest_python_deepseek_coder_6_7b_python_devstral_24b.json",
            predictions_path=self.predictions_path,
            gt_cwe_extraction_function=lambda x: str(int(x.split("-")[-1].strip())),
            # gt_cwe_extraction_function=lambda x: x,
            alpha_path=output_path,
            detailed_result_path=detailed_result_path
        )
        
    
    def get_distance_stats(self):
        weaakness_cwe_graph = self.create_weakness_graph()
        return weaakness_cwe_graph.compute_distance_statistics()
        
if __name__ == "__main__":
    EDA_PATH = "code_security/eda_results.json"
    sven = "services/CodeSecurity/experiments/SAST/SVEN_sast_transformed_any_match.json"
    security_eval = "services/CodeSecurity/experiments/SAST/SecurityEval_sast_transformed_any_match.json"

    alpha_instance = ALPHA(
        predictions_path=sven,
        # predictions_path=security_eval,
        eda_path=EDA_PATH
    )
    
    alpha_instance.get_distance_stats()