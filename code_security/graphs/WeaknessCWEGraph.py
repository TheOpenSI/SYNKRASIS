import networkx as nx
import json

from typing import Dict, Set, List, Tuple
from collections import defaultdict, deque

from code_security.graphs.BaseCWEGraph import BaseCWEGraph

class WeaknessCWEGraph(BaseCWEGraph):
    """
    Weakness-only CWE graph (excludes views and categories).
    Focuses on semantic weakness relationships without organisational overhead.
    """
    
    WEAKNESS_TYPES = {
        'pillar_weakness',
        'class_weakness',
        'base_weakness',
        'variant_weakness',
        'compound_weakness',
        'chain_weakness'
    }
    
    
    def _build_graph(self):
        """Build graph with only weakness types."""
        self.directed = nx.DiGraph()
        
        # Add weakness nodes only
        for cwe_id, cwe_info in self.data.items():
            if self._should_include_node(cwe_id, cwe_info):
                self.directed.add_node(cwe_id, type=cwe_info['type'])
        
        # Add edges between weaknesses
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
        """Include only weakness types."""
        cwe_type = cwe_info.get('type', '')
        return cwe_type in self.WEAKNESS_TYPES   