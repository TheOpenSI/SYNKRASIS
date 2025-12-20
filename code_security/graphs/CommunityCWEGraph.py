from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from networkx.algorithms import community
from code_security.graphs.BaseCWEGraph import BaseCWEGraph

class CommunityCWEGraph:
    """
    Wrapper that adds community detection to any BaseCWEGraph.
    
    Uses Louvain algorithm to detect natural clusters of CWEs.
    """
    
    def __init__(self, base_graph: BaseCWEGraph):
        """
        Initialise with a base graph.
        
        Args:
            base_graph: Instance of FullCWEGraph or WeaknessCWEGraph
        """
        self.base_graph = base_graph
        self.data = base_graph.data
        self.directed = base_graph.directed
        self.undirected = base_graph.undirected
        
        # Detect communities
        self.communities = None
        self.cwe_to_community = None
        self._detect_communities()
    
    def _detect_communities(self):
        """
        Detect communities using Louvain algorithm.
        
        Louvain optimises modularity, a measure of community quality.
        """
        self.communities = list(
            community.louvain_communities(self.undirected, seed=42)
        )
        
        # Create mapping
        self.cwe_to_community = {}
        for comm_idx, comm_set in enumerate(self.communities):
            for cwe_id in comm_set:
                self.cwe_to_community[cwe_id] = comm_idx
    
    # Delegate distance methods to base graph
    def get_distance(self, cwe1: str, cwe2: str) -> int:
        """Calculate distance using base graph."""
        return self.base_graph.get_distance(cwe1, cwe2)
    
    def get_distance_with_path(self, cwe1: str, cwe2: str) -> Tuple[int, List[str]]:
        """Get distance with path using base graph."""
        return self.base_graph.get_distance_with_path(cwe1, cwe2)
    
    def get_distance_with_details(self, cwe1: str, cwe2: str) -> Dict:
        """Get distance details using base graph."""
        return self.base_graph.get_distance_with_details(cwe1, cwe2)
    
    def batch_distance_calculation(self, cwe_pairs: List[Tuple[str, str]]) -> Dict:
        """Batch distance calculation using base graph."""
        return self.base_graph.batch_distance_calculation(cwe_pairs)
    
    def calculate_llm_score(self, true_cwe: str, predicted_cwe: str,
                           max_points: int = 100,
                           scoring_tiers: Dict[int, float] = None) -> Dict:
        """Distance-based scoring using base graph."""
        return self.base_graph.calculate_llm_score(true_cwe, predicted_cwe, 
                                                    max_points, scoring_tiers)
    
    def get_statistics(self) -> Dict:
        """Get statistics from base graph."""
        return self.base_graph.get_statistics()
    
    def get_cwe_info(self, cwe_id: str) -> Optional[Dict]:
        """Get CWE info from base graph."""
        return self.base_graph.get_cwe_info(cwe_id)
    
    # Community-specific methods
    def get_community(self, cwe_id: str) -> Optional[int]:
        """
        Get the community index for a CWE.
        
        Returns:
            Community index or None if CWE not found
        """
        return self.cwe_to_community.get(cwe_id)
    
    def are_in_same_community(self, cwe1: str, cwe2: str) -> bool:
        """Check if two CWEs are in the same community."""
        comm1 = self.get_community(cwe1)
        comm2 = self.get_community(cwe2)
        
        if comm1 is None or comm2 is None:
            return False
        
        return comm1 == comm2
    
    def get_community_members(self, community_idx: int) -> Set[str]:
        """
        Get all CWE IDs in a specific community.
        
        Returns:
            Set of CWE IDs
        """
        if 0 <= community_idx < len(self.communities):
            return self.communities[community_idx]
        return set()
    
    def calculate_llm_score_community_based(self, true_cwe: str, predicted_cwe: str,
                                           max_points: int = 100,
                                           same_community_score: float = 0.5) -> Dict:
        """
        Score based on community membership.
        
        Args:
            true_cwe: Ground truth
            predicted_cwe: Prediction
            max_points: Max score for exact match
            same_community_score: Multiplier if in same community (default: 0.5)
            
        Returns:
            Score dictionary
        """
        # Exact match
        if true_cwe == predicted_cwe:
            return {
                'score': max_points,
                'multiplier': 1.0,
                'same_community': True,
                'explanation': 'Exact match - perfect prediction',
                'true_cwe': true_cwe,
                'predicted_cwe': predicted_cwe,
                'true_community': self.get_community(true_cwe),
                'predicted_community': self.get_community(predicted_cwe)
            }
        
        # Get communities
        true_comm = self.get_community(true_cwe)
        pred_comm = self.get_community(predicted_cwe)
        
        # Handle missing
        if true_comm is None or pred_comm is None:
            missing_cwe = []
            if true_comm is None:
                missing_cwe.append(f"CWE-{true_cwe}")
            if pred_comm is None:
                missing_cwe.append(f"CWE-{predicted_cwe}")
            
            return {
                'score': 0,
                'multiplier': 0.0,
                'same_community': False,
                'explanation': f"Error: {', '.join(missing_cwe)} not in graph",
                'true_cwe': true_cwe,
                'predicted_cwe': predicted_cwe,
                'true_community': true_comm,
                'predicted_community': pred_comm
            }
        
        # Check same community
        same_community = (true_comm == pred_comm)
        
        if same_community:
            score = int(max_points * same_community_score)
            explanation = f"Same community (#{true_comm}) - related weaknesses"
        else:
            score = 0
            explanation = f"Different communities (#{true_comm} vs #{pred_comm}) - unrelated"
        
        return {
            'score': score,
            'multiplier': same_community_score if same_community else 0.0,
            'same_community': same_community,
            'explanation': explanation,
            'true_cwe': true_cwe,
            'predicted_cwe': predicted_cwe,
            'true_community': true_comm,
            'predicted_community': pred_comm,
            'true_type': self.data.get(true_cwe, {}).get('type', 'Unknown'),
            'predicted_type': self.data.get(predicted_cwe, {}).get('type', 'Unknown')
        }
    
    def get_community_analysis(self) -> Dict:
        """
        Get detailed community analysis.
        
        Returns:
            Dictionary with statistics and community details
        """
        sorted_communities = sorted(enumerate(self.communities),
                                   key=lambda x: len(x[1]),
                                   reverse=True)
        
        analysis = {
            'num_communities': len(self.communities),
            'communities': []
        }
        
        for comm_idx, comm_set in sorted_communities:
            type_counts = defaultdict(int)
            for cwe_id in comm_set:
                cwe_type = self.data.get(cwe_id, {}).get('type', 'Unknown')
                type_counts[cwe_type] += 1
            
            sample_members = list(comm_set)[:10]
            
            comm_info = {
                'community_id': comm_idx,
                'size': len(comm_set),
                'type_distribution': dict(type_counts),
                'sample_members': sample_members,
                'sample_member_types': [
                    self.data.get(cwe_id, {}).get('type', 'Unknown')
                    for cwe_id in sample_members
                ]
            }
            
            analysis['communities'].append(comm_info)
        
        # Statistics
        sizes = [len(c) for c in self.communities]
        analysis['size_statistics'] = {
            'min_size': min(sizes),
            'max_size': max(sizes),
            'avg_size': sum(sizes) / len(sizes),
            'median_size': sorted(sizes)[len(sizes) // 2]
        }
        
        return analysis