# Adaptive Learning via Penalty in Hierarchical Assessment

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

from code_security.graphs.FullCWEGraph import FullCWEGraph
from code_security.graphs.WeaknessCWEGraph import WeaknessCWEGraph

class ALPHA:
    def __init__(self, eda_path: str):
        self.eda_path = eda_path


    def create_full_graph(self) -> FullCWEGraph:
        """Createservices/CodeSecurity/cwe_analysis/eda_results.json full CWE graph including all types."""
        return FullCWEGraph(self.eda_path)
    
    
    def create_weakness_graph(self) -> WeaknessCWEGraph:
        """Create weakness-only CWE graph (recommended for LLM evaluation)."""
        return WeaknessCWEGraph(self.eda_path)

    def main(self):
        weakness_cwe_graph = self.create_weakness_graph()
        # weakness_cwe_graph.calculate_and_save_depths('code_security/depth_analysis/cwe_depths.json')
        weakness_cwe_graph.get_alpha(
            predictions_path="services/CodeSecurity/experiments/exp_dir_SVEN_python_1/SVEN_python_qwen2_5_coder_32b_python_mistral_latest_python_qwen2_5_coder_latest_python_llama3_1_latest_python_phi4_latest_python_deepseek_coder_6_7b_python_devstral_24b.json",
            gt_cwe_extraction_function=lambda x: str(int(x.split("-")[-1].strip())),
            alpha_path="code_security/alpha_results/alpha_scores_sven_1.json",
            detailed_result_path="code_security/alpha_results/detailed_results_sven_1.json"
        )

if __name__ == "__main__":
    alpha = ALPHA(eda_path="code_security/eda_results.json")
    alpha.main()