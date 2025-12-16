import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

from code_security.FullCWEGraph import FullCWEGraph
from code_security.WeaknessCWEGraph import WeaknessCWEGraph

class VDC:
    def __init__(self, eda_path: str):
        self.eda_path = eda_path


    def create_full_graph(self) -> FullCWEGraph:
        """Createservices/CodeSecurity/cwe_analysis/eda_results.json full CWE graph including all types."""
        return FullCWEGraph(self.eda_path)
    
    
    def create_weakness_graph(self) -> WeaknessCWEGraph:
        """Create weakness-only CWE graph (recommended for LLM evaluation)."""
        return WeaknessCWEGraph(self.eda_path)

    def main(self):
        # Create different graph types
        print("\nCreating Full Graph...")
        full_graph = self.create_full_graph()
        print(f"   Nodes: {full_graph.directed.number_of_nodes()}")
        print(f"   Edges: {full_graph.directed.number_of_edges()}")
        
        print("\nCreating Weakness-Only Graph...")
        weakness_graph = self.create_weakness_graph()
        print(f"   Nodes: {weakness_graph.directed.number_of_nodes()}")
        print(f"   Edges: {weakness_graph.directed.number_of_edges()}")
        
        # Samples
        print("\n" + "="*70)
        print("DISTANCE CALCULATION EXAMPLES")
        print("="*70)
        
        print("\nFull Graph:")
        dist_full = full_graph.get_distance("79", "327")
        print(f"  CWE-79 to CWE-327: {dist_full} hops")
        
        print("\nWeakness-Only Graph:")
        dist_weak = weakness_graph.get_distance("79", "327")
        print(f"  CWE-79 to CWE-327: {dist_weak} hops")
        
        # LLM scoring example
        print("\n" + "="*70)
        print("LLM SCORING EXAMPLES")
        print("="*70)
        
        print("\nDistance-Based Scoring:")
        result = weakness_graph.calculate_llm_score("79", "80")
        print(f"  True: CWE-{result['true_cwe']}, Predicted: CWE-{result['predicted_cwe']}")
        print(f"  Score: {result['score']}/100")
        print(f"  Explanation: {result['explanation']}")


if __name__ == "__main__":
    vdc = VDC(eda_path="code_security/eda_results.json")
    vdc.main()