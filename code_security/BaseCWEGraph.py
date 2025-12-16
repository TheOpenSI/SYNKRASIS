from abc import ABC, abstractmethod
import json
import networkx as nx
from typing import Dict, List, Tuple, Optional

class BaseCWEGraph(ABC):
    """
    Abstract base class for CWE graph analysis.
    Defines the interface that all graph implementations must provide.
    """
    
    def __init__(self, eda_results_path: str):
        """
        Initialise the graph analyser.
        
        Args:
            eda_results_path: Path to eda_results.json file
        """
        self.eda_results_path = eda_results_path
        self.data = self._load_data()
        self.directed = None
        self.undirected = None
        self._build_graph()


    def _load_data(self) -> Dict:
        """Load the EDA results JSON file."""
        with open(self.eda_results_path, 'r') as f:
            return json.load(f)


    @abstractmethod
    def _build_graph(self):
        """Build the graph structure. Must be implemented by subclasses."""
        pass


    @abstractmethod
    def _should_include_node(self, cwe_id: str, cwe_info: Dict) -> bool:
        """Determine if a CWE should be included in this graph."""
        pass


    def get_distance(self, cwe1: str, cwe2: str) -> int:
        """
        Calculate shortest path distance between two CWEs.
        
        Args:
            cwe1: First CWE ID (without "CWE-" prefix)
            cwe2: Second CWE ID (without "CWE-" prefix)
            
        Returns:
            Distance (0 for same CWE, -1 if no path exists)
        """
        if cwe1 == cwe2:
            return 0
        
        if cwe1 not in self.undirected.nodes() or cwe2 not in self.undirected.nodes():
            return -1
        
        try:
            path = nx.shortest_path(self.undirected, cwe1, cwe2)
            return len(path) - 1
        except nx.NetworkXNoPath:
            return -1


    def get_distance_with_path(self, cwe1: str, cwe2: str) -> Tuple[int, List[str]]:
        """
        Calculate distance and return the path.
        
        Returns:
            Tuple of (distance, path_list)
        """
        if cwe1 == cwe2:
            return 0, [cwe1]
        
        if cwe1 not in self.undirected.nodes():
            return -1, [f"CWE-{cwe1} not in graph"]
        if cwe2 not in self.undirected.nodes():
            return -1, [f"CWE-{cwe2} not in graph"]
        
        try:
            path = nx.shortest_path(self.undirected, cwe1, cwe2)
            return len(path) - 1, path
        except nx.NetworkXNoPath:
            return -1, ["No path exists"]


    def get_distance_with_details(self, cwe1: str, cwe2: str) -> Dict:
        """
        Get comprehensive distance information.
        
        Returns:
            Dictionary with distance, path, types, etc.
        """
        distance, path = self.get_distance_with_path(cwe1, cwe2)
        
        result = {
            'distance': distance,
            'path': path,
            'connected': distance >= 0,
            'cwe1_type': self.data.get(cwe1, {}).get('type', 'Unknown'),
            'cwe2_type': self.data.get(cwe2, {}).get('type', 'Unknown')
        }
        
        if distance >= 0 and isinstance(path, list) and len(path) > 0:
            result['path_types'] = [
                self.data.get(cwe_id, {}).get('type', 'Unknown') 
                for cwe_id in path
            ]
        else:
            result['path_types'] = []
        
        return result


    def batch_distance_calculation(self, cwe_pairs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], int]:
        """
        Calculate distances for multiple CWE pairs.
        
        Returns:
            Dictionary mapping (cwe1, cwe2) -> distance
        """
        results = {}
        for cwe1, cwe2 in cwe_pairs:
            distance = self.get_distance(cwe1, cwe2)
            results[(cwe1, cwe2)] = distance
        return results


    def get_statistics(self) -> Dict:
        """Get basic graph statistics."""
        components = list(nx.connected_components(self.undirected))
        
        stats = {
            'num_nodes': self.directed.number_of_nodes(),
            'num_edges': self.directed.number_of_edges(),
            'num_components': len(components),
            'largest_component_size': len(max(components, key=len)) if components else 0,
        }
        
        if components:
            largest_component = max(components, key=len)
            largest_subgraph = self.undirected.subgraph(largest_component)
            
            if len(largest_component) > 1:
                try:
                    stats['diameter'] = nx.diameter(largest_subgraph)
                    stats['avg_shortest_path'] = nx.average_shortest_path_length(largest_subgraph)
                except:
                    stats['diameter'] = None
                    stats['avg_shortest_path'] = None
        
        return stats


    def get_cwe_info(self, cwe_id: str) -> Optional[Dict]:
        """Get information about a specific CWE."""
        if cwe_id not in self.data:
            return None
        
        cwe_data = self.data[cwe_id]
        
        return {
            'id': cwe_id,
            'type': cwe_data.get('type', 'Unknown'),
            'parents': cwe_data.get('parents', []),
            'children': cwe_data.get('children', []),
            'num_parents': len(cwe_data.get('parents', [])),
            'num_children': len(cwe_data.get('children', [])),
            'total_relationships': len(cwe_data.get('immediate_relationships', []))
        }


    def get_relationship_direction(self, cwe_pred: str, cwe_true: str) -> str:
        """
        Determine the hierarchical relationship direction between prediction and ground truth.
        
        Args:
            cwe_pred: Predicted CWE ID (without "CWE-" prefix)
            cwe_true: Ground truth CWE ID (without "CWE-" prefix)
        
        Returns:
            'ancestor': cwe_pred is ancestor of cwe_true (going up/generalising)
            'descendant': cwe_pred is descendant of cwe_true (going down/over-specifying)
            'lateral': neither ancestor nor descendant (different branches or same level)
            'unknown': one or both CWEs not in graph
        """
        # Check if both nodes exist in directed graph
        if cwe_pred not in self.directed.nodes() or cwe_true not in self.directed.nodes():
            return 'unknown'
        
        # Same CWE - technically no direction
        if cwe_pred == cwe_true:
            return 'exact'
        
        # Check if pred is ancestor of true (path from pred → true in directed graph)
        try:
            nx.shortest_path(self.directed, cwe_pred, cwe_true)
            return 'ancestor'  # Prediction is more general (going up)
        except nx.NetworkXNoPath:
            pass
        
        # Check if pred is descendant of true (path from true → pred in directed graph)
        try:
            nx.shortest_path(self.directed, cwe_true, cwe_pred)
            return 'descendant'  # Prediction is more specific (going down)
        except nx.NetworkXNoPath:
            pass
        
        # Neither ancestor nor descendant - lateral relationship
        return 'lateral'


    def calculate_penalty_score(self, 
                            true_cwe: str, 
                            predicted_cwe: str,
                            alpha_up: float = 2.0,
                            alpha_lateral: float = 1.5,
                            alpha_down: float = 1.2,
                            max_penalty: float = 3.0) -> Dict:
        """
        Calculate penalty score using hierarchical distance and direction.
        
        Implements the penalty function:
            P(c_pred, c_true) = d(c_pred, c_true) × α(c_pred, c_true)
        
        where \alpha depends on the direction of the error:
            - \alpha_up: prediction is ancestor (more general) 
            - \alpha_down: prediction is descendant (more specific)
            - \alpha_lateral: prediction is lateral (different branch)
        
        Args:
            true_cwe: Ground truth CWE ID
            predicted_cwe: Predicted CWE ID
            alpha_up: Penalty multiplier for generalising errors (default: 2.0)
            alpha_lateral: Penalty multiplier for lateral errors (default: 1.5)
            alpha_down: Penalty multiplier for over-specifying errors (default: 1.2)
            max_penalty: Maximum penalty for out-of-graph or disconnected predictions (default: 10.0)
        
        Returns:
            Dictionary containing:
                - penalty: Final penalty score
                - distance: Shortest path distance
                - direction: Relationship direction ('ancestor'/'descendant'/'lateral'/'unknown')
                - alpha: Multiplier used
                - explanation: Human-readable description
                - path: List of CWE IDs in shortest path
                - true_cwe: Ground truth CWE ID
                - predicted_cwe: Predicted CWE ID
                - true_type: Type of ground truth CWE
                - predicted_type: Type of predicted CWE (if in graph)
        """
        # Perfect prediction
        if true_cwe == predicted_cwe:
            return {
                'penalty': 0.0,
                'distance': 0,
                'direction': 'exact',
                'alpha': 1.0,
                'explanation': 'Exact match - perfect prediction',
                'path': [true_cwe],
                'true_cwe': true_cwe,
                'predicted_cwe': predicted_cwe,
                'true_type': self.data.get(true_cwe, {}).get('type', 'Unknown'),
                'predicted_type': self.data.get(predicted_cwe, {}).get('type', 'Unknown')
            }
        
        # Get distance and path
        distance, path = self.get_distance_with_path(predicted_cwe, true_cwe)
        
        # Handle cases where CWEs are not in graph or not connected
        if distance == -1:
            if predicted_cwe not in self.directed.nodes():
                explanation = f"Predicted CWE-{predicted_cwe} not in graph - likely a View/Category or invalid CWE"
                predicted_type = 'Not in graph'
            elif true_cwe not in self.directed.nodes():
                explanation = f"Ground truth CWE-{true_cwe} not in graph"
                predicted_type = self.data.get(predicted_cwe, {}).get('type', 'Unknown')
            else:
                explanation = "CWEs not connected - completely unrelated weakness types"
                predicted_type = self.data.get(predicted_cwe, {}).get('type', 'Unknown')
            
            return {
                'penalty': max_penalty,
                'distance': -1,
                'direction': 'unknown',
                'alpha': max_penalty,  # Effectively max penalty
                'explanation': explanation,
                'path': path,
                'true_cwe': true_cwe,
                'predicted_cwe': predicted_cwe,
                'true_type': self.data.get(true_cwe, {}).get('type', 'Unknown'),
                'predicted_type': predicted_type
            }
        
        # Determine direction and select appropriate alpha
        direction = self.get_relationship_direction(predicted_cwe, true_cwe)
        
        if direction == 'ancestor':
            alpha = alpha_up
            direction_description = "more general (going up hierarchy)"
        elif direction == 'descendant':
            alpha = alpha_down
            direction_description = "more specific (going down hierarchy)"
        elif direction == 'lateral':
            alpha = alpha_lateral
            direction_description = "lateral relationship (different branch)"
        else:
            # Shouldn't happen if distance >= 0, but safety check
            alpha = alpha_lateral
            direction_description = "unclear relationship"
        
        # Calculate penalty
        penalty = distance * alpha
        
        # Generate explanation
        if distance == 1:
            distance_description = "1 hop away"
        else:
            distance_description = f"{distance} hops away"
        
        explanation = (f"Prediction is {distance_description} and {direction_description}. "
                    f"Penalty = {distance} × {alpha} = {penalty:.2f}")
        
        return {
            'penalty': penalty,
            'distance': distance,
            'direction': direction,
            'alpha': alpha,
            'explanation': explanation,
            'path': path,
            'true_cwe': true_cwe,
            'predicted_cwe': predicted_cwe,
            'true_type': self.data.get(true_cwe, {}).get('type', 'Unknown'),
            'predicted_type': self.data.get(predicted_cwe, {}).get('type', 'Unknown')
        }
