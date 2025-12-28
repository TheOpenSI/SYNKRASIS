# ========================================================================================
# Base CWE Graph Class
#
# Child class to implement -
#   - _build_graph(): Build the graph structure
#   - _should_include_node(cwe_id, cwe_info): Determine if a CWE should be included
#
# Usage:
#   - get_distance(cwe1, cwe2): Get shortest path distance between two CWEs
#   - get_distance_with_path(cwe1, cwe2): Get distance and path
#   - get_distance_with_details(cwe1, cwe2): Get detailed distance info
#   - batch_distance_calculation(cwe_pairs): Batch distance calculation
#   - get_statistics(): Get basic graph statistics
#   - get_cwe_info(cwe_id): Get information about a specific CWE
#   - get_relationship_direction(cwe_pred, cwe_true): Get relationship direction
#   - calculate_penalty_score(true_cwe, predicted_cwe): Calculate penalty score
#   - calculate_and_save_depths(output_path): Calculate and save depths to file
# ========================================================================================

from abc import ABC, abstractmethod
import json
import networkx as nx
from typing import Dict, List, Tuple, Optional, Set, DefaultDict
from pathlib import Path

class BaseCWEGraph(ABC):
    """
    Abstract base class for CWE graph analysis.
    Defines the interface that all graph implementations must provide.
    """
    
    def __init__(self, 
                 eda_results_path: str = "code_security/eda_results.json",
                 depth_analysis_path: str = "code_security/depth_analysis/cwe_depths.json"):
        """
        Initialise the graph analyser.
        
        Args:
            eda_results_path: Path to eda_results.json file
        """
        self.eda_results_path = eda_results_path
        self.depth_analysis_path = depth_analysis_path
        self.data = self._load_data()
        self.directed = None
        self.undirected = None
        self._build_graph()
        self.max_alpha = 2.5 # Default max alpha for out-of-graph predictions
        self.alpha_up = 2.0   # Default alpha for generalising errors
        self.alpha_lateral = 1.8  # Default alpha for lateral errors
        self.least_penalty = 1.1  # Default least penalty for over-specifying errors
        self._initialise_depth_cache()
        stats = self.get_statistics()
        graph_diameter = stats['diameter']
        # Default max penalty (distance) \for unknown/unconnected CWEs
        self.max_penalty = int(graph_diameter/2) + 1


    @abstractmethod
    def _build_graph(self):
        """Build the graph structure. Must be implemented by subclasses."""
        pass


    @abstractmethod
    def _should_include_node(self, cwe_id: str, cwe_info: Dict) -> bool:
        """Determine if a CWE should be included in this graph."""
        pass


    def _initialise_depth_cache(self):
        """
        Initialise depth-related caches from saved depth file or calculate fresh.
        Call this in __init__ after _build_graph().
        
        Creates:
            - self.cwe_depths: Dict[str, int] - depth for each CWE
            - self.type_max_depths: Dict[str, int] - max depth per type
        """
        with open(self.depth_analysis_path, "r") as f:
            depth_data = json.load(f)
        
        self.cwe_depths = {cwe_id: info['depth'] for cwe_id, info in depth_data.items()}
        print("Loaded depths from cwe_depths.json")
        
        # Calculate type max depths
        self.type_max_depths = {}
        type_depths = {}
        
        for cwe_id, depth in self.cwe_depths.items():
            if cwe_id in self.data:
                cwe_type = self.data[cwe_id].get('type', 'Unknown')
                if cwe_type not in type_depths:
                    type_depths[cwe_type] = []
                type_depths[cwe_type].append(depth)
        
        for cwe_type, depths in type_depths.items():
            self.type_max_depths[cwe_type] = max(depths)
        
        print(f"Type max depths: {self.type_max_depths}")


    def _load_data(self) -> Dict:
        """Load the EDA results JSON file."""
        with open(self.eda_results_path, 'r') as f:
            return json.load(f)


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
                            predicted_cwe: str) -> Dict:
        """
        Calculate penalty score using hierarchical distance and direction.
        
        Implements the penalty function:
            P(c_pred, c_true) = d(c_pred, c_true) * \alpha(c_pred, c_true)
        
        where \alpha depends on the direction of the error:
            - \alpha_up: prediction is ancestor (more general) 
            - \alpha_down: prediction is descendant (more specific)
            - \alpha_lateral: prediction is lateral (different branch)
        
        Args:
            true_cwe: Ground truth CWE ID
            predicted_cwe: Predicted CWE ID
        
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
        if distance == -1 or predicted_cwe is None:
            if predicted_cwe not in self.directed.nodes():
                explanation = (f"Predicted CWE-{predicted_cwe} not in graph - "
               "likely a View/Category or invalid CWE")
                predicted_type = 'Not in graph'
            elif true_cwe not in self.directed.nodes():
                explanation = f"Ground truth CWE-{true_cwe} not in graph"
                predicted_type = self.data.get(predicted_cwe, {}).get('type', 'Unknown')
            else:
                explanation = "CWEs not connected - completely unrelated weakness types"
                predicted_type = self.data.get(predicted_cwe, {}).get('type', 'Unknown')
            
            return {
                'penalty': self.max_penalty * self.max_alpha,
                'distance': -1,
                'direction': 'unknown',
                'alpha': self.max_alpha,  # Effectively max penalty
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
            alpha = self.alpha_up
            direction_description = "more general (going up hierarchy)"
        elif direction == 'descendant':
            alpha = self._get_alpha_down_adaptive(true_cwe)
            direction_description = "more specific (going down hierarchy)"
        elif direction == 'lateral':
            alpha = self.alpha_lateral
            direction_description = "lateral relationship (different branch)"
        else:
            # Shouldn't happen if distance >= 0, but safety check
            alpha = self.alpha_lateral
            direction_description = "unclear relationship"
        
        # Calculate penalty
        penalty = distance * alpha
        
        # Generate explanation
        if distance == 1:
            distance_description = "1 hop away"
        else:
            distance_description = f"{distance} hops away"
        
        explanation = (f"Prediction is {distance_description} and {direction_description}. "
                    f"Penalty = {distance} * {alpha} = {penalty:.2f}")
        
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

    
    def _calculate_max_depth_to_leaf(self, cwe_id: str, visited: Set[str] = None) -> int:
        """
        Calculate maximum distance from this CWE to any leaf node in its subtree.
        A leaf is defined as a CWE with no children.
        
        Args:
            cwe_id: CWE ID (without "CWE-" prefix)
            visited: Set of visited nodes for cycle detection
            
        Returns:
            Maximum depth to any leaf (0 if this CWE is itself a leaf)
        """
        if visited is None:
            visited = set()
        
        # Cycle detection
        if cwe_id in visited or cwe_id not in self.data:
            return 0
        
        visited.add(cwe_id)
        
        # Get children from data
        children = self.data[cwe_id].get('children', [])
        
        # Base case: leaf node (no children)
        if not children:
            return 0
        
        # Recursive case: find max depth among all children
        max_depth = 0
        for child_id in children:
            if child_id in self.directed.nodes():  # Only process children in graph
                child_depth = self._calculate_max_depth_to_leaf(child_id, visited.copy())
                max_depth = max(max_depth, child_depth)
        
        return max_depth + 1


    def calculate_and_save_depths(self, output_path: str) -> Dict[str, int]:
        """
        Calculate max depth to leaf for all CWEs and save with metadata.
        
        Output JSON structure:
        {
        "cwe_id": {
            "type": "base_weakness",
            "depth": 1,
            "parents_count": 2,
            "children_count": 1,
            "immediate_relationships_count": 3
        },
        ...
        }
        
        Args:
            output_path: Path to save the depth analysis JSON
            
        Returns:
            Dictionary mapping CWE ID -> depth value
        """
        print("Calculating depths for all CWEs in graph...")
        
        depths = {}
        depth_analysis = {}
        
        total = len(self.directed.nodes())
        for i, cwe_id in enumerate(self.directed.nodes(), 1):
            if i % 100 == 0:
                print(f"  Progress: {i}/{total}")
            
            # Calculate depth
            depth = self._calculate_max_depth_to_leaf(cwe_id)
            depths[cwe_id] = depth
            
            # Gather metadata from data
            cwe_data = self.data.get(cwe_id, {})
            
            depth_analysis[cwe_id] = {
                'type': cwe_data.get('type', 'Unknown'),
                'depth': depth,
                'parents_count': len(cwe_data.get('parents', [])),
                'children_count': len(cwe_data.get('children', [])),
                'immediate_relationships_count': len(cwe_data.get('immediate_relationships', []))
            }
        
        print(f"Calculated depths for {len(depths)} CWEs")
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(depth_analysis, f, indent=2)
        
        print(f"Depth analysis saved to {output_path}")
        
        return depths
    
    
    def _get_alpha_down_adaptive(self, true_cwe: str) -> float:
        """Calculate adaptive alpha_down based on CWE depth."""
        
        # Get depth and type
        depth = self.cwe_depths.get(true_cwe, 0)
        cwe_type = self.data[true_cwe]['type']
        
        # Get type max depth
        type_max = self.type_max_depths.get(cwe_type, 1)
        
        # Calculate alpha
        if type_max > 0:
            normalised = depth / type_max
        else:
            normalised = 0
        
        alpha = self.alpha_lateral - (self.alpha_lateral - self.least_penalty) * normalised
        return alpha
    
    
    def get_alpha(self,
                  predictions_path: str,
                  gt_cwe_extraction_function: callable,
                  alpha_path: str,
                  detailed_result_path: str) -> None:
        """
        Get ALPHA score for a dataset.
        
        Args:
            predictions_path: Path to predictions JSON file
            dataset_path: Path to dataset JSON file
            gt_key: Key in dataset entries for ground truth CWE ID
        """
        alpha_score: DefaultDict[str, int] = DefaultDict(int)
        detailed_result: List[Dict] = []
        
        with open(predictions_path, "r") as pred_f:
            predictions = json.load(pred_f)
        
        for prediction in predictions:
            sample_index = prediction["sample_index"]
            gt = gt_cwe_extraction_function(prediction["true_label"])
            llm_predictions = prediction["analysis"]
            
            penalty_scores: Dict[str, int] = {}
            for llm_prediction in llm_predictions:
                llm_model = llm_prediction["llm_model"]
                predicted_cwe_list = llm_prediction["parsed_response"]["cwe"]
                # print(predicted_cwe_list)
                predicted_cwe = predicted_cwe_list[-1] \
                    if len(predicted_cwe_list) > 0 \
                        else None                   
                predicted_cwe = predicted_cwe.replace("CWE-", "") if predicted_cwe is not None else None
                penalty = self.calculate_penalty_score(true_cwe=gt, predicted_cwe=predicted_cwe)
                alpha_score[llm_model] += penalty["penalty"]
                penalty_scores[llm_model] = penalty["penalty"]
            
            detailed_result.append({
                "sample_index": sample_index,
                "ground_truth": gt,
                "penalty_scores": penalty_scores
            })
            
        # create parent dirs
        Path(alpha_path).parent.mkdir(parents=True, exist_ok=True)
        Path(detailed_result_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save alpha scores
        with open(alpha_path, "w") as alpha_f:
            json.dump(alpha_score, alpha_f, indent=2)
        print(f"Saved ALPHA scores to {alpha_path}")
        
        # Save detailed results
        with open(detailed_result_path, "w") as detail_f:
            json.dump(detailed_result, detail_f, indent=2)
        print(f"Saved detailed results to {detailed_result_path}")
        
        
    def compute_distance_statistics(self) -> Dict:
        """
        Compute statistics about in-graph distances.
        Used to justify out-of-graph penalty settings.
        
        Returns:
            Dictionary with median, mean, and distribution of distances
        """
        print("Computing distance statistics for all CWE pairs...")
        
        nodes = list(self.directed.nodes())
        n = len(nodes)
        total_pairs = n * (n - 1) // 2  # Number of unique pairs
        
        distances = []
        
        # Calculate distances for all unique pairs
        for i, cwe1 in enumerate(nodes):
            if i % 50 == 0:
                print(f"  Progress: {i}/{n} nodes processed")
            
            for cwe2 in nodes[i+1:]:  # Only pairs where i < j (avoid duplicates)
                dist = self.get_distance(cwe1, cwe2)
                if dist > 0:  # Exclude same CWE (dist=0) and disconnected (-1)
                    distances.append(dist)
        
        # Calculate statistics
        distances_sorted = sorted(distances)
        n_distances = len(distances)
        
        median = distances_sorted[n_distances // 2] if n_distances > 0 else 0
        mean = sum(distances) / n_distances if n_distances > 0 else 0
        
        # Distribution
        from collections import Counter
        dist_counts = Counter(distances)
        
        stats = self.get_statistics()
        diameter = stats['diameter']
        
        result = {
            'median_distance': median,
            'mean_distance': mean,
            'total_pairs': total_pairs,
            'connected_pairs': n_distances,
            'diameter': diameter,
            'diameter_over_2': diameter / 2,
            'distance_distribution': dict(dist_counts),
            'comparison': {
                'median_vs_diameter_half': f"Median {median} ≈ diameter/2 {diameter/2:.1f}",
                'recommended_doog': int(diameter/2) + 1
            }
        }
        
        print(f"\nDistance Statistics:")
        print(f"  Median: {median}")
        print(f"  Mean: {mean:.2f}")
        print(f"  Diameter: {diameter}")
        print(f"  Diameter/2: {diameter/2:.1f}")
        print(f"  Recommended d_oog: {int(diameter/2) + 1}")
        print(f"  Total unique pairs: {total_pairs}")
        print(f"  Connected pairs (dist > 0): {len(distances)}")
        
        return result