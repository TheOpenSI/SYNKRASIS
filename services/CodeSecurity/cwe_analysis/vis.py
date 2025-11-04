# =============================================================================================
# Builds a network graph of CWE relationships and exports as interactive HTML
# Saves three types of relationships as JSON:
#   1. Immediate relationships (direct parent-child from API data)
#   2. Distance map (hop distance between all CWE pairs)
#   3. Root categories (which of the 10 root nodes each CWE belongs to)
# =============================================================================================

import os
import json
from pathlib import Path
from pyvis.network import Network
import networkx as nx
from collections import defaultdict, deque

class CWEGraphBuilder:
    def __init__(self, analysis_dir: str):
        self.analysis_dir = analysis_dir
        self.graph = nx.DiGraph()  # Directed graph for analysis
        self.cwe_data = {}  # Store loaded data
        
        # EDA
        self.cwe_types = defaultdict(int)
        
    def load_all_cwes(self):
        """
        Load all processed CWE files from analysis directory
        """
        print("Loading CWE data...")
        cwe_data = {}
        
        for cwe_folder in Path(self.analysis_dir).iterdir():
            if not cwe_folder.is_dir() or not cwe_folder.name.startswith("CWE-"):
                continue
                
            cwe_id = cwe_folder.name.split("-")[1]
            processed_file = cwe_folder / f"cwe_{cwe_id}_processed_results.json"
            
            if processed_file.exists():
                with open(processed_file, 'r') as f:
                    data = json.load(f)
                    cwe_data[cwe_id] = data['results']
        
        self.cwe_data = cwe_data
        print(f"Loaded {len(cwe_data)} CWEs from {self.analysis_dir}")
        return cwe_data
    
    
    def build_graph(self):
        """
        Build networkx directed graph from CWE data
        """
        print("Building graph...")
        
        # First pass: create all nodes
        for cwe_id, results in self.cwe_data.items():
            # Check deprecation status
            cwe_info = results.get(f'/cwe/{cwe_id}')
            if not cwe_info or cwe_info.get("is_deprecated", False):
                continue
            
            # EDA
            self.cwe_types[cwe_info.get("Type", "Unknown")] += 1
            
            # Get weakness information
            weakness_info = results.get(f'/cwe/weakness/{cwe_id}')
            if weakness_info:
                node_label = f"{cwe_id}: {weakness_info.get('Name', 'Unknown')}"
                self.graph.add_node(
                    cwe_id,
                    label=node_label,
                    title=cwe_info.get("Type", "Unknown"),
                    type='weakness'
                )
        
        # Second pass: create edges
        for cwe_id, results in self.cwe_data.items():
            # Skip deprecated CWEs
            cwe_info = results.get(f'/cwe/{cwe_id}')
            if not cwe_info or cwe_info.get("is_deprecated", False):
                continue
            
            # Get relationship information
            parents_info = results.get(f'/cwe/{cwe_id}/parents', {})
            children_info = results.get(f'/cwe/{cwe_id}/children', {})
            
            # Add parent edges (parent -> child direction)
            for parent_data in parents_info.get('weakness_parents', []):
                parent_id = parent_data[1]  # parent_data is [relationship_type, id]
                relationship_type = parent_data[0]
                
                # Only add edge if parent node exists
                if parent_id in self.graph:
                    self.graph.add_edge(
                        parent_id, 
                        cwe_id, 
                        relationship=f'parent_{relationship_type}'
                    )
            
            # Add child edges (current -> child direction)
            for child_data in children_info.get('weakness_children', []):
                child_id = child_data[1]  # child_data is [relationship_type, id]
                relationship_type = child_data[0]
                
                # Only add edge if child node exists
                if child_id in self.graph:
                    self.graph.add_edge(
                        cwe_id, 
                        child_id, 
                        relationship=f'child_{relationship_type}'
                    )
        
        print(f"Graph built: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")
    
    def save_immediate_relationships(self, 
                                    output_file: str = "cwe_immediate_relationships.json"):
        """
        Save immediate parent-child relationships directly from API data.
        
        Output format:
        {
            "cwe_id": {
                "immediate_parents": ["parent1", "parent2", ...],
                "immediate_children": ["child1", "child2", ...]
            }
        }
        """
        print("\nSaving immediate relationships...")
        relationships = {}
        
        for cwe_id, results in self.cwe_data.items():
            # Skip deprecated CWEs
            cwe_info = results.get(f'/cwe/{cwe_id}')
            if not cwe_info or cwe_info.get("is_deprecated", False):
                continue
            
            # Skip if not in graph
            if cwe_id not in self.graph:
                continue
            
            parents_info = results.get(f'/cwe/{cwe_id}/parents', {})
            children_info = results.get(f'/cwe/{cwe_id}/children', {})
            
            # Extract just the IDs
            immediate_parents = [p[1] for p in parents_info.get('weakness_parents', [])]
            immediate_children = [c[1] for c in children_info.get('weakness_children', [])]
            
            # Filter to only include CWEs that exist in our graph
            immediate_parents = [p for p in immediate_parents if p in self.graph]
            immediate_children = [c for c in immediate_children if c in self.graph]
            
            relationships[cwe_id] = {
                'immediate_parents': sorted(immediate_parents),
                'immediate_children': sorted(immediate_children)
            }
        
        # Save to JSON
        with open(output_file, 'w') as f:
            json.dump(relationships, f, indent=2)
        
        print(f"Immediate relationships saved to {output_file}")
        print(f"Total CWEs: {len(relationships)}")
        
        # Statistics
        total_parents = sum(len(v['immediate_parents']) for v in relationships.values())
        total_children = sum(len(v['immediate_children']) for v in relationships.values())
        print(f"Total immediate parent links: {total_parents}")
        print(f"Total immediate child links: {total_children}")
        
        return relationships
    
    def save_distance_map(self, 
                         output_file: str = "cwe_distance_map.json"):
        """
        Compute and save shortest path distances between all CWE pairs.
        Uses undirected graph so distance is symmetric.
        
        Output format:
        {
            "cwe_id": {
                "other_cwe_id": distance,
                ...
            }
        }
        """
        print("\nComputing distance map (this may take a while)...")
        
        # Convert to undirected graph for distance calculation
        undirected = self.graph.to_undirected()
        
        distance_map = {}
        nodes = list(undirected.nodes())
        total_nodes = len(nodes)
        
        # Compute shortest paths from each node
        for i, source in enumerate(nodes):
            if (i + 1) % 100 == 0:
                print(f"  Processing node {i + 1}/{total_nodes}...")
            
            # Get shortest path lengths from this source to all reachable nodes
            lengths = nx.single_source_shortest_path_length(undirected, source)
            
            # Store distances (excluding self)
            distance_map[source] = {
                target: dist 
                for target, dist in lengths.items() 
                if target != source
            }
        
        # Save to JSON
        print("Saving distance map...")
        with open(output_file, 'w') as f:
            json.dump(distance_map, f, indent=2)
        
        print(f"Distance map saved to {output_file}")
        
        # Statistics
        total_distances = sum(len(v) for v in distance_map.values())
        print(f"Total distance entries: {total_distances:,}")
        
        # Calculate file size
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"File size: {file_size_mb:.2f} MB")
        
        # Distance distribution
        all_distances = []
        for source_distances in distance_map.values():
            all_distances.extend(source_distances.values())
        
        if all_distances:
            max_dist = max(all_distances)
            avg_dist = sum(all_distances) / len(all_distances)
            print(f"Maximum distance: {max_dist}")
            print(f"Average distance: {avg_dist:.2f}")
            
            # Show distribution
            dist_counts = defaultdict(int)
            for d in all_distances:
                dist_counts[d] += 1
            
            print("\nDistance distribution:")
            for dist in sorted(dist_counts.keys()):
                count = dist_counts[dist]
                percentage = (count / len(all_distances)) * 100
                print(f"  {dist} hops: {count:,} pairs ({percentage:.1f}%)")
        
        return distance_map
    
    def save_root_categories(self, 
                            output_file: str = "cwe_root_categories.json"):
        """
        Assign each CWE to its root ancestor(s).
        
        Output format:
        {
            "cwe_id": "root_id",  // or list of root_ids if multiple roots
            ...
        }
        """
        print("\nComputing root categories...")
        
        # Find root nodes (nodes with no parents)
        root_nodes = [n for n in self.graph.nodes() 
                     if self.graph.in_degree(n) == 0]
        
        print(f"Found {len(root_nodes)} root nodes: {sorted(root_nodes)}")
        
        root_categories = {}
        
        for node in self.graph.nodes():
            # Find all ancestors
            ancestors = nx.ancestors(self.graph, node)
            
            # Find which roots this node descends from
            node_roots = [r for r in root_nodes if r in ancestors]
            
            # If node is itself a root
            if node in root_nodes:
                node_roots = [node]
            
            # If no roots found but node has ancestors, something's wrong
            # This shouldn't happen if we correctly identified roots
            if not node_roots and ancestors:
                # Find the highest ancestors
                node_roots = [a for a in ancestors 
                            if self.graph.in_degree(a) == 0]
            
            # Store the root(s)
            if len(node_roots) == 1:
                root_categories[node] = node_roots[0]
            elif len(node_roots) > 1:
                root_categories[node] = node_roots  # Multiple roots
            else:
                # Node is isolated or is itself a root
                root_categories[node] = node
        
        # Save to JSON
        with open(output_file, 'w') as f:
            json.dump(root_categories, f, indent=2)
        
        print(f"Root categories saved to {output_file}")
        
        # Statistics - group by root
        root_distribution = defaultdict(list)
        for cwe, root in root_categories.items():
            if isinstance(root, list):
                for r in root:
                    root_distribution[r].append(cwe)
            else:
                root_distribution[root].append(cwe)
        
        print("\nCWEs per root category:")
        for root in sorted(root_distribution.keys()):
            count = len(root_distribution[root])
            print(f"  Root {root}: {count} CWEs")
        
        return root_categories
    
    def export_interactive_html(self, 
                                output_file: str = "cwe_graph.html"):
        """Export graph as interactive HTML using pyvis (undirected, no arrows)"""
        print("\nExporting interactive visualisation...")
        
        net = Network(
            height="1080px",
            width="100%",
            bgcolor="#222222",
            font_color="white",
            directed=False  # No arrows!
        )
        
        # Configure physics for better layout
        net.barnes_hut(
            gravity=-8000,
            central_gravity=0.3,
            spring_length=200,
            spring_strength=0.001,
            damping=0.09
        )
        
        # Add nodes
        for node, attrs in self.graph.nodes(data=True):
            net.add_node(
                node,
                label=attrs.get('label', node),
                title=attrs.get('title', ''),
                color="#4ecdc4",
                size=10
            )
        
        # Add edges (will appear undirected without arrows)
        for source, target, attrs in self.graph.edges(data=True):
            relation = attrs.get('relationship', '')
            net.add_edge(source, target, color="#4ecdc4", title=relation)
        
        # Save the graph
        net.save_graph(output_file)
        print(f"Interactive graph exported to {output_file}")
        return output_file
    
    def get_stats(self):
        """Print comprehensive graph statistics"""
        print("\n" + "="*70)
        print("GRAPH STATISTICS")
        print("="*70)
        print(f"Total nodes: {self.graph.number_of_nodes()}")
        print(f"Total edges: {self.graph.number_of_edges()}")
        
        if self.graph.number_of_nodes() > 0:
            # Root nodes (no parents)
            root_nodes = [n for n in self.graph.nodes() 
                         if self.graph.in_degree(n) == 0]
            print(f"Root nodes (no parents): {len(root_nodes)}")
            print(f"  Root IDs: {sorted(root_nodes)}")
            
            # Leaf nodes (no children)
            leaf_nodes = [n for n in self.graph.nodes() 
                         if self.graph.out_degree(n) == 0]
            print(f"Leaf nodes (no children): {len(leaf_nodes)}")
            
            # Average degree
            avg_in_degree = sum(d for n, d in self.graph.in_degree()) / self.graph.number_of_nodes()
            avg_out_degree = sum(d for n, d in self.graph.out_degree()) / self.graph.number_of_nodes()
            print(f"Average parents per node: {avg_in_degree:.2f}")
            print(f"Average children per node: {avg_out_degree:.2f}")
        
        # Connected components
        undirected = self.graph.to_undirected()
        num_components = nx.number_connected_components(undirected)
        print(f"Number of connected components: {num_components}")
        print("="*70)


def main():
    """Main execution function"""
    # Configuration
    analysis_dir = ("services/CodeSecurity/cwe_analysis/analysis")
    output_dir = ("services/CodeSecurity/cwe_analysis/")
    
    # Initialize builder
    builder = CWEGraphBuilder(analysis_dir)
    
    # Load data
    builder.load_all_cwes()
    
    # Build graph
    builder.build_graph()
    
    # Show statistics
    builder.get_stats()
    
    # Export visualisation (undirected, no arrows)
    builder.export_interactive_html(
        output_file=output_dir + "cwe_graph.html"
    )
    
    # Save File 1: Immediate relationships
    builder.save_immediate_relationships(
        output_file=output_dir + "cwe_immediate_relationships.json"
    )
    
    # Save File 2: Distance map (all distances)
    builder.save_distance_map(
        output_file=output_dir + "cwe_distance_map.json"
    )
    
    # Save File 3: Root categories
    builder.save_root_categories(
        output_file=output_dir + "cwe_root_categories.json"
    )
    
    print("\n" + "="*70)
    print("COMPLETE!")
    print("="*70)
    print("\nGenerated files:")
    print(f"1. Interactive graph: {output_dir}cwe_graph.html")
    print(f"2. Immediate relationships: {output_dir}cwe_immediate_relationships.json")
    print(f"3. Distance map: {output_dir}cwe_distance_map.json")
    print(f"4. Root categories: {output_dir}cwe_root_categories.json")


if __name__ == "__main__":
    main()