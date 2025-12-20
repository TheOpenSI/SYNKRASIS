import networkx as nx

from typing import Dict
from code_security.graphs.BaseCWEGraph import BaseCWEGraph

class FullCWEGraph(BaseCWEGraph):
    """
    Full CWE graph including all types: weaknesses, views, and categories.
    
    Use this when you need the complete CWE taxonomy structure.
    Not recommended for LLM evaluation (views create artificial shortcuts).
    """
    
    def _build_graph(self):
        """Build graph with all CWE types."""
        self.directed = nx.DiGraph()
        
        # Add all nodes
        for cwe_id, cwe_info in self.data.items():
            if self._should_include_node(cwe_id, cwe_info):
                self.directed.add_node(cwe_id, type=cwe_info['type'])
        
        # Add all edges
        for cwe_id, cwe_info in self.data.items():
            if cwe_id not in self.directed.nodes():
                continue
            
            for child_id in cwe_info['children']:
                if child_id in self.directed.nodes():
                    self.directed.add_edge(cwe_id, child_id, relationship='parent_of')
            
            for parent_id in cwe_info['parents']:
                if parent_id in self.directed.nodes():
                    self.directed.add_edge(parent_id, cwe_id, relationship='parent_of')
        
        self.undirected = self.directed.to_undirected()
    
    def _should_include_node(self, cwe_id: str, cwe_info: Dict) -> bool:
        """Include all non-deprecated CWEs."""
        cwe_type = cwe_info.get('type', '')
        return 'deprecated' not in cwe_type.lower()