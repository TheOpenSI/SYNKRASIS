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
        weakness_cwe_graph.calculate_and_save_depths('code_security/depth_analysis/cwe_depths.json')

if __name__ == "__main__":
    alpha = ALPHA(eda_path="code_security/eda_results.json")
    alpha.main()