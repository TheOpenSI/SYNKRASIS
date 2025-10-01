import os
import json
from pathlib import Path
from pyvis.network import Network
import networkx as nx

class CWEGraphBuilder:
    def __init__(self, analysis_dir: str):
        self.analysis_dir = analysis_dir
        self.graph = nx.DiGraph()
        self.categories = set()
        
    def load_all_cwes(self):
        """Load all processed CWE files from analysis directory"""
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
        
        return cwe_data
    
    def build_graph(self, cwe_data: dict):
        """Build networkx graph from CWE data"""
        
        # First pass: create all nodes
        for cwe_id, results in cwe_data.items():
            # deprication status
            depricated =  results.get(f'/cwe/{cwe_id}')["is_deprecated"]
            if depricated:
                continue
            
            # weakness, endpoint 2
            weakness_info = results.get(f'/cwe/weakness/{cwe_id}')
            if weakness_info:
                node_label = f"{cwe_id}: {weakness_info.get('Name', 'Unknown')}"
                self.graph.add_node(
                    cwe_id,
                    label=node_label,
                    title=results.get(f'/cwe/{cwe_id}')["Type"],
                    type='weakness'
                )
        
        # Second pass: create edges and category nodes
        for cwe_id, results in cwe_data.items():
            # deprication status
            depricated =  results.get(f'/cwe/{cwe_id}')["is_deprecated"]
            if depricated:
                continue
            
            # relationships, endpoints 3 and 4
            parents_info = results.get(f'/cwe/{cwe_id}/parents', {})
            children_info = results.get(f'/cwe/{cwe_id}/children', {})
            
            if not parents_info or not children_info:
                continue
            
            # parent edges
            for parent_id in parents_info.get('weakness_parents', []):
                self.graph.add_edge(parent_id[1], cwe_id, relationship=f'parent_{parent_id[0]}')
            
            # for parent_id in parents_info.get('category_parents', []):
            #     self.categories.add(parent_id)
            #     if not self.graph.has_node(parent_id):
            #         self.graph.add_node(
            #             parent_id,
            #             label=f"{parent_id} (C)",
            #             title="Category",
            #             type='category'
            #         )
            #     self.graph.add_edge(parent_id, cwe_id, relationship='category_parent')
            
            # Add child edges
            for child_id in children_info.get('weakness_children', []):
                self.graph.add_edge(cwe_id, child_id[1], relationship=f'child_{child_id[0]}')
            
            # for child_id in children_info.get('category_children', []):
            #     self.categories.add(child_id)
            #     if not self.graph.has_node(child_id):
            #         self.graph.add_node(
            #             child_id,
            #             label=f"{child_id} (C)",
            #             title="Category",
            #             type='category'
            #         )
            #     self.graph.add_edge(cwe_id, child_id, relationship='category_child')
    
    def export_interactive_html(self, 
                                output_file: str = ("/home/s448780/workspace_hcc4/"
                                                    "SYNKRASIS/services/"
                                                    "CodeSecurity/cwe_analysis/cwe_graph.html")):
        """Export graph as interactive HTML using pyvis"""
        
        net = Network(
            height="1080px",
            width="100%",
            bgcolor="#222222",
            font_color="white",
            directed=True
        )
        
        # physics
        net.barnes_hut(
            gravity=-8000,
            central_gravity=0.3,
            spring_length=200,
            spring_strength=0.001,
            damping=0.09
        )
        
        # Add nodes with colors based on type
        for node, attrs in self.graph.nodes(data=True):
            color = "#ff6b6b" if attrs.get('type') == 'category' else "#4ecdc4"
            net.add_node(
                node,
                label=attrs.get('label', node),
                title=attrs.get('title', ''),
                color=color,
                size=20 if attrs.get('type') == 'category' else 10
            )
        
        # Add edges
        for source, target, attrs in self.graph.edges(data=True):
            relation = attrs.get('relationship', '')
            # if 'parent' in relation:
            #     edge_color = "#ff6b6b" 
            # else:
            #     edge_color = "#4ecdc4"
            edge_color = "#4ecdc4"
            net.add_edge(source, target, color=edge_color, title=relation)
        
        # Use show_buttons and save_graph instead of show
        # net.show_buttons(filter_=['physics'])
        net.save_graph(output_file)
        print(f"Graph exported to {output_file}")
        return output_file
    
    def get_stats(self):
        """Print graph statistics"""
        print(f"Total nodes: {self.graph.number_of_nodes()}")
        print(f"Total edges: {self.graph.number_of_edges()}")
        print(f"Category nodes: {len(self.categories)}")
        print(f"Weakness nodes: {self.graph.number_of_nodes() - len(self.categories)}")
    
    def compute_and_save_relationships(self, 
                                       output_file: str = "cwe_relationships.json"):
        """
        Compute transitive closure of all CWE relationships and save to JSON.
        For each CWE, finds all related CWEs (ancestors + descendants).
        """
        relationships = {}
        
        print("Computing relationships...")
        for node in self.graph.nodes():
            # Get all ancestors (following parent edges backwards)
            ancestors = nx.ancestors(self.graph, node)
            
            # Get all descendants (following child edges forwards)
            descendants = nx.descendants(self.graph, node)
            
            # Combine and sort
            related = sorted(ancestors | descendants)
            relationships[node] = related
        
        # Save to JSON
        with open(output_file, 'w') as f:
            json.dump(relationships, f, indent=2)
        
        print(f"Relationships saved to {output_file}")
        print(f"Total CWEs: {len(relationships)}")
        
        # Some stats
        total_relationships = sum(len(v) for v in relationships.values())
        avg_relationships = total_relationships / len(relationships) if relationships else 0
        print(f"Total relationships: {total_relationships}")
        print(f"Average relationships per CWE: {avg_relationships:.1f}")
        
        return relationships


if __name__ == "__main__":
    builder = CWEGraphBuilder(
        "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/cwe_analysis/analysis"
    )
    
    print("Loading CWE data...")
    cwe_data = builder.load_all_cwes()
    print(f"Loaded {len(cwe_data)} CWEs")
    
    print("Building graph...")
    builder.build_graph(cwe_data)
    
    builder.get_stats()
    
    print("Exporting to HTML...")
    builder.export_interactive_html()
    
    print("\nComputing relationships...")
    builder.compute_and_save_relationships(("/home/s448780/workspace_hcc4/SYNKRASIS/"
                                            "services/CodeSecurity/"
                                            "cwe_analysis/cwe_relationships.json"))